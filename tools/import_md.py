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
# Metadata carry-over from the exporter (tools/export_md.py) — lets a
# round-tripped file preserve year / accent on each chapter.
META_COMMENT = re.compile(r"<!--\s*spatial-deck:\s*(.+?)\s*-->")
META_KV = re.compile(r"(\w+)\s*=\s*(.+?)(?=\s+\w+\s*=|\s*$)")
META_BLOCK_START = re.compile(r"^<!--\s*spatial-deck\s*$")
META_BLOCK_KV = re.compile(r"^(\w+):\s*(.*?)\s*$")

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


def _make_chapter() -> dict:
    return {"lesson_title": "", "lesson_tagline_parts": [], "cases": [], "meta": {}}


def parse(md: str) -> list[dict]:
    """Return a list of chapter dicts (one per `#` heading). No LLM."""
    chapters: list[dict] = []
    chapter: dict | None = None
    current: dict | None = None
    pending_subtitle_for_current = False
    pending_tagline_for_chapter = False
    in_meta_block = False

    def ensure_chapter() -> dict:
        nonlocal chapter
        if chapter is None:
            chapter = _make_chapter()
            chapters.append(chapter)
        return chapter

    for raw_line in md.splitlines():
        line = raw_line.rstrip()

        if in_meta_block:
            if line.strip() == "-->":
                in_meta_block = False
                continue
            kv = META_BLOCK_KV.match(line.strip())
            if kv:
                ch = ensure_chapter()
                ch["meta"][kv.group(1)] = kv.group(2)
            continue
        if META_BLOCK_START.match(line.strip()):
            in_meta_block = True
            ensure_chapter()
            continue

        if not line.strip():
            continue

        # `---` thematic break between chapters in exporter output.
        if line.strip() == "---" and chapter is not None:
            chapter = None
            current = None
            pending_subtitle_for_current = False
            pending_tagline_for_chapter = False
            continue

        meta_m = META_COMMENT.search(line)
        if meta_m:
            ch = ensure_chapter()
            for k, v in META_KV.findall(meta_m.group(1)):
                ch["meta"][k] = v
            continue

        m = H2.match(line)
        if m:
            ch = ensure_chapter()
            current = _make_case()
            current["title"] = m.group(1).strip()
            ch["cases"].append(current)
            pending_subtitle_for_current = True
            pending_tagline_for_chapter = False
            continue

        m = H1.match(line)
        if m:
            # Always start a fresh chapter on H1.
            chapter = _make_chapter()
            chapter["lesson_title"] = m.group(1).strip()
            chapters.append(chapter)
            current = None
            pending_subtitle_for_current = False
            pending_tagline_for_chapter = True
            continue

        m = BULLET.match(line)
        if m and current is not None:
            text = m.group(1).strip()
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
            ch = ensure_chapter()
            if pending_tagline_for_chapter or not ch["lesson_tagline_parts"]:
                ch["lesson_tagline_parts"].append(line.strip())
        elif pending_subtitle_for_current and not current["subtitle"]:
            current["subtitle"] = line.strip()
        elif pending_subtitle_for_current and current["subtitle"]:
            current["subtitle"] = (current["subtitle"] + " " + line.strip()).strip()
        else:
            current["notes"] = (current["notes"] + " " + line.strip()).strip() if current["notes"] else line.strip()

    return chapters


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

    parsed_chapters = parse(args.md.read_text())
    # Drop empty chapters (no title, no tagline, no cases).
    parsed_chapters = [c for c in parsed_chapters if c["lesson_title"] or c["cases"] or c["lesson_tagline_parts"]]
    if not parsed_chapters:
        print("ERROR: no `#` or `##` headings found in markdown", file=sys.stderr)
        return 3

    total_cases = sum(len(c["cases"]) for c in parsed_chapters)
    if total_cases == 0:
        print("ERROR: no `## slide` headings found in markdown", file=sys.stderr)
        return 3

    print(f"[md] {len(parsed_chapters)} chapter(s), {total_cases} slides parsed from {args.md.name}", file=sys.stderr)

    if args.tighten:
        n = 0
        for parsed in parsed_chapters:
            for c in parsed["cases"]:
                n += 1
                try:
                    c["bullets"] = tighten_bullets(c["title"], c["bullets"])
                    print(f"  [slide {n}/{total_cases}] tightened: {c['title'][:50]}", file=sys.stderr)
                except Exception as e:
                    print(f"  [slide {n}] tighten failed ({e}); keeping raw", file=sys.stderr)

    built: list[dict] = []
    for i, parsed in enumerate(parsed_chapters):
        cases = parsed["cases"]
        for c in cases:
            if not c["notes"]:
                del c["notes"]
        meta = parsed["meta"]
        year = meta.get("year") or (args.chapter if len(parsed_chapters) == 1 else f"{args.chapter}-{i+1}")
        accent = meta.get("accent") or args.accent
        if accent not in ("teal", "purple", "amber", "rose"):
            accent = args.accent
        tagline = " ".join(parsed["lesson_tagline_parts"]).strip()
        # Meta-provided title overrides the H1 when the original had line breaks.
        meta_title = meta.get("title", "").replace("\\n", "\n") if meta.get("title") else ""
        title = meta_title or parsed["lesson_title"] or f"Imported: {args.md.stem}"
        built.append({
            "year": year,
            "accent": accent,
            "lesson": {
                "title": title,
                "short": meta.get("short", year),
                "tagline": tagline or f"Imported from {args.md.name}. Edit this tagline and the cases below to match your narrative.",
                "tags": meta.get("tags", ""),
            },
            "cases": cases,
        })

    stem = SAFE.sub("-", args.md.stem).strip("-").lower() or "deck"
    digest = hashlib.sha1(args.md.read_bytes()).hexdigest()[:8]
    out_path = args.out or (REPO_ROOT / "tools" / f"imported-{stem}-{digest}.json")
    payload = built if len(built) > 1 else built[0]
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    try:
        rel = str(out_path.relative_to(REPO_ROOT))
    except ValueError:
        rel = str(out_path)
    print(f"[done] Wrote {rel} ({len(built)} chapter(s), {total_cases} cases)", file=sys.stderr)
    print(f"[next] python3 tools/merge_sections.py {rel}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
