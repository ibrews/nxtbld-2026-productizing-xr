"""Export the SECTIONS array as a Markdown file — the inverse of import_md.py.

Round-trips the convention used by the markdown importer:
  # Chapter title           (one per chapter)
  tagline paragraph
  ## Case title             (one per case)
  subtitle paragraph
  ![alt](media/foo.png)
  - bullet 1
  - bullet 2
  > speaker note

Useful for:
  - Editing a deck in your favorite Markdown editor, then re-importing.
  - Handing a static outline to a human reviewer or an AI collaborator.
  - Diffing deck content in a format `git diff` renders nicely.

Usage:
    python3 tools/export_md.py > my-deck.md
    python3 tools/export_md.py --html other.html --out outline.md
    python3 tools/export_md.py --chapter 1   # export one chapter only
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lint_deck import extract_sections  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HTML = REPO_ROOT / "index.html"


def emit_case(c: dict) -> list[str]:
    lines: list[str] = []
    title = (c.get("title") or "").replace("\n", " ").strip() or "(untitled)"
    lines.append(f"## {title}")
    lines.append("")
    subtitle = (c.get("subtitle") or "").strip()
    if subtitle:
        lines.append(subtitle)
        lines.append("")
    img = (c.get("img") or "").strip()
    # Skip pseudo-values that aren't real paths.
    if img and not img.startswith(("MEDIA_CYCLER", "IFRAME:")):
        alt = (c.get("alt") or subtitle or title or "image").strip()
        lines.append(f"![{alt}]({img})")
        lines.append("")
    bullets = c.get("bullets") or []
    for b in bullets:
        if isinstance(b, str) and b.strip():
            lines.append(f"- {b.strip()}")
    if bullets:
        lines.append("")
    notes = (c.get("notes") or "").strip()
    if notes:
        for ln in notes.splitlines():
            lines.append(f"> {ln}")
        lines.append("")
    return lines


def emit_chapter(ch: dict) -> list[str]:
    lines: list[str] = []
    lesson = ch.get("lesson") or {}
    ch_title = (lesson.get("title") or ch.get("year") or "Chapter").replace("\n", " / ").strip()
    lines.append(f"# {ch_title}")
    lines.append("")
    tagline = (lesson.get("tagline") or "").strip()
    if tagline:
        lines.append(tagline)
        lines.append("")
    # Surface lesson-level config as a YAML-ish HTML comment so re-imports round-trip.
    meta_pairs: list[tuple[str, str]] = []
    year = (ch.get("year") or "").strip()
    accent = (ch.get("accent") or "").strip()
    raw_title = (lesson.get("title") or "").strip()
    short = (lesson.get("short") or "").strip()
    tags = (lesson.get("tags") or "").strip()
    if year:     meta_pairs.append(("year", year))
    if accent:   meta_pairs.append(("accent", accent))
    if raw_title and "\n" in raw_title:
        meta_pairs.append(("title", raw_title.replace("\n", "\\n")))
    if short:    meta_pairs.append(("short", short))
    if tags:     meta_pairs.append(("tags", tags))
    if meta_pairs:
        lines.append("<!-- spatial-deck")
        for k, v in meta_pairs:
            lines.append(f"{k}: {v}")
        lines.append("-->")
        lines.append("")
    for c in ch.get("cases") or []:
        lines.extend(emit_case(c))
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--out", type=Path, default=None, help="write to file (default: stdout)")
    ap.add_argument("--chapter", type=int, default=None, help="index of single chapter to export")
    args = ap.parse_args()

    sections = extract_sections(args.html)
    if args.chapter is not None:
        if args.chapter < 0 or args.chapter >= len(sections):
            print(f"ERROR: chapter index {args.chapter} out of range (0..{len(sections)-1})", file=sys.stderr)
            return 2
        chapters = [sections[args.chapter]]
    else:
        chapters = sections

    out_lines: list[str] = []
    for i, ch in enumerate(chapters):
        if i > 0:
            out_lines.append("---")
            out_lines.append("")
        out_lines.extend(emit_chapter(ch))

    text = "\n".join(out_lines).rstrip() + "\n"
    if args.out:
        args.out.write_text(text)
        print(f"[done] Wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
