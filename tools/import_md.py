"""Import a Markdown file into Spatial Deck's SECTIONS array.

Convention (strict, predictable — no LLM needed for structure):

    # Chapter / deck title            → lesson.title
    (optional paragraph)              → lesson.tagline
    ## Slide title                    → case { title }
    (optional paragraph)              → case.subtitle  (first paragraph under h2)
    - bullet                          → case.bullets[]
    * bullet                          → case.bullets[]
    ![alt](media/foo.jpg)             → case.img (first image wins; alt becomes
                                         subtitle if none already set)
    > note line                       → case.notes (blockquote text, joined)

Pipeline:
  1. Regex parse — deterministic, no LLM required.
  2. Optional --tighten flag sends each slide's bullets to llama3.1:8b@Sam
     for punch-ification (rare; the structure usually arrives clean).
  3. Output is a SECTIONS-compatible chapter JSON ready for
     tools/merge_sections.py.

Usage:
    python3 tools/import_md.py talk.md
    python3 tools/import_md.py talk.md --chapter "TALK 2026" --accent amber
    python3 tools/import_md.py talk.md --tighten   # LLM bullet rewrite
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fleet_client import call_json, ENDPOINTS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

H1 = re.compile(r"^#\s+(.+?)\s*$")
H2 = re.compile(r"^##\s+(.+?)\s*$")
BULLET = re.compile(r"^\s*[-*+]\s+(.+?)\s*$")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
BLOCKQUOTE = re.compile(r"^>\s?(.*)$")
SAFE = re.compile(r"[^a-zA-Z0-9]+")

TIGHTEN_PROMPT = """Rewrite these slide bullets into tight, declarative, punchy lines.
Slide title: {title!r}
Bullets (raw):
{bullets}

Rules:
- Keep the count the same (one output bullet per input bullet).
- Each bullet <= 140 chars, no markdown, no emoji unless in original.
- Preserve numbers, proper nouns, and technical terms exactly.
- Drop filler words. Never invent facts.

Output a JSON object with ONE key:
  bullets — array of strings, same length as input.
"""


def _make_case() -> dict:
    return {"title": "", "subtitle": "", "img": "", "bullets": [], "notes": ""}


def parse(md: str) -> dict:
    """Return a chapter dict with lesson + cases. No LLM."""
    lesson_title = ""
    lesson_tagline_parts: list[str] = []
    cases: list[dict] = []
    current: dict | None = None
    seen_h1 = False
    # Track whether we're in lesson-tagline-paragraph mode vs case-subtitle mode.
    # A paragraph is the first non-empty, non-list, non-image, non-heading line
    # block after the heading.
    pending_subtitle_for_current = False

    for raw_line in md.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            # Blank line ends an in-progress paragraph, but doesn't cancel
            # the "still waiting for a subtitle after the h2" state — a lot
            # of markdown puts a blank line between heading and paragraph.
            continue

        m = H2.match(line)
        if m:
            current = _make_case()
            current["title"] = m.group(1).strip()
            cases.append(current)
            pending_subtitle_for_current = True
            continue

        m = H1.match(line)
        if m:
            if not seen_h1:
                lesson_title = m.group(1).strip()
                seen_h1 = True
            # Additional H1s are treated as chapter-title overrides — ignore.
            pending_subtitle_for_current = False
            continue

        m = BULLET.match(line)
        if m and current is not None:
            text = m.group(1).strip()
            # Strip inline image from bullet line.
            img_m = IMAGE.search(text)
            if img_m and not current["img"]:
                current["img"] = img_m.group(2).strip()
                if not current["subtitle"] and img_m.group(1).strip():
                    current["subtitle"] = img_m.group(1).strip()
                text = IMAGE.sub("", text).strip(" -|")
            if text:
                current["bullets"].append(text)
            pending_subtitle_for_current = False
            continue

        img_m = IMAGE.search(line)
        if img_m and current is not None:
            if not current["img"]:
                current["img"] = img_m.group(2).strip()
                if not current["subtitle"] and img_m.group(1).strip():
                    current["subtitle"] = img_m.group(1).strip()
            pending_subtitle_for_current = False
            continue

        bq = BLOCKQUOTE.match(line)
        if bq and current is not None:
            note_text = bq.group(1).strip()
            if note_text:
                current["notes"] = (current["notes"] + " " + note_text).strip() if current["notes"] else note_text
            continue

        # Plain paragraph line.
        if current is None:
            # Belongs to the chapter tagline.
            lesson_tagline_parts.append(line.strip())
        elif pending_subtitle_for_current and not current["subtitle"]:
            current["subtitle"] = line.strip()
            # Allow multi-line subtitle to join on subsequent lines.
        elif pending_subtitle_for_current and current["subtitle"]:
            current["subtitle"] = (current["subtitle"] + " " + line.strip()).strip()
        else:
            # Treat as additional note text.
            current["notes"] = (current["notes"] + " " + line.strip()).strip() if current["notes"] else line.strip()

    return {
        "lesson_title": lesson_title,
        "lesson_tagline": " ".join(lesson_tagline_parts).strip(),
        "cases": cases,
    }


# (model, host) pairs tried in order. Sam llama3.1:8b is the fleet winner for
# short structured rewrites; qwen3:8b@MBP is a local fallback when Sam is
# offline or flaky. Both are small — no RAM contention against this session.
TIGHTEN_ROUTES = [
    ("llama3.1:8b", "sam"),
    ("qwen3:8b",    "mbp"),
]


def tighten_bullets(title: str, bullets: list[str]) -> list[str]:
    if not bullets:
        return bullets
    joined = "\n".join(f"- {b}" for b in bullets)
    prompt = TIGHTEN_PROMPT.format(title=title, bullets=joined)
    last_err: Exception | None = None
    for model, host in TIGHTEN_ROUTES:
        try:
            data = call_json(model, prompt, endpoint=ENDPOINTS[host], required_keys=["bullets"])
            out = data.get("bullets")
            if not isinstance(out, list) or len(out) != len(bullets) or not all(isinstance(x, str) for x in out):
                raise ValueError("malformed bullets")
            return [x.strip() for x in out]
        except Exception as e:
            last_err = e
            print(f"    [tighten] {model}@{host} failed: {e}", file=sys.stderr)
    raise RuntimeError(f"all tighten routes failed; last error: {last_err}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("md", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--chapter", default="IMPORTED", help="year/chapter label")
    ap.add_argument("--accent", default="teal", choices=["teal", "purple", "amber", "rose"])
    ap.add_argument("--tighten", action="store_true", help="LLM-tighten each slide's bullets (llama3.1:8b@Sam)")
    args = ap.parse_args()

    if not args.md.exists():
        print(f"ERROR: {args.md} not found", file=sys.stderr)
        return 2

    parsed = parse(args.md.read_text())
    cases = parsed["cases"]
    if not cases:
        print("ERROR: no `## slide` headings found in markdown", file=sys.stderr)
        return 3

    print(f"[md] {len(cases)} slides parsed from {args.md.name}", file=sys.stderr)

    if args.tighten:
        for i, c in enumerate(cases, 1):
            try:
                c["bullets"] = tighten_bullets(c["title"], c["bullets"])
                print(f"  [slide {i}/{len(cases)}] tightened: {c['title'][:50]}", file=sys.stderr)
            except Exception as e:
                print(f"  [slide {i}] tighten failed ({e}); keeping raw", file=sys.stderr)

    # Drop empty keys for cleaner JSON.
    for c in cases:
        if not c["notes"]:
            del c["notes"]

    chapter = {
        "year": args.chapter,
        "accent": args.accent,
        "lesson": {
            "title": parsed["lesson_title"] or f"Imported: {args.md.stem}",
            "short": args.chapter,
            "tagline": parsed["lesson_tagline"] or f"Imported from {args.md.name}. Edit this tagline and the cases below to match your narrative.",
            "tags": "",
        },
        "cases": cases,
    }

    stem = SAFE.sub("-", args.md.stem).strip("-").lower() or "deck"
    digest = hashlib.sha1(args.md.read_bytes()).hexdigest()[:8]
    out_path = args.out or (REPO_ROOT / "tools" / f"imported-{stem}-{digest}.json")
    out_path.write_text(json.dumps(chapter, indent=2, ensure_ascii=False))
    print(f"[done] Wrote {out_path.relative_to(REPO_ROOT)} ({len(cases)} cases)", file=sys.stderr)
    print(f"[next] python3 tools/merge_sections.py {out_path.relative_to(REPO_ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
