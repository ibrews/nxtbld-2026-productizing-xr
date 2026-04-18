"""Splice an imported chapter JSON into index.html's SECTIONS array.

Looks for sentinel comments inside the SECTIONS array:
    // ── IMPORTED START ──
    // ── IMPORTED END ──

If the sentinels don't exist yet, they're inserted just before the closing
`];` of the SECTIONS array. Subsequent imports replace whatever sits
between the sentinels (so merge is idempotent).

Usage:
    python3 tools/merge_sections.py tools/imported-deck-abcd1234.json
    python3 tools/merge_sections.py path/to/chapter.json --html other.html
    python3 tools/merge_sections.py path/to/chapter.json --dry-run
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HTML = REPO_ROOT / "index.html"

START = "// ── IMPORTED START ──"
END = "// ── IMPORTED END ──"

SECTIONS_CLOSE = re.compile(r"^(\s*)\];\s*$", re.MULTILINE)
SECTIONS_OPEN = re.compile(r"^\s*const\s+SECTIONS\s*=\s*\[", re.MULTILINE)


def js_string(s: str) -> str:
    """Emit a JS single-quoted string literal with minimal escaping."""
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n") + "'"


def emit_case(c: dict, indent: str = "      ") -> str:
    title = js_string(c.get("title", ""))
    subtitle = js_string(c.get("subtitle", ""))
    img = js_string(c.get("img", ""))
    bullets = c.get("bullets", [])
    bullets_js = "[" + ",".join(js_string(b) for b in bullets) + "]"
    parts = [f"title:{title}", f"subtitle:{subtitle}", f"img:{img}", f"bullets:{bullets_js}"]
    if c.get("notes"):
        parts.append(f"notes:{js_string(c['notes'])}")
    return indent + "{ " + ", ".join(parts) + " },"


def emit_chapter(ch: dict) -> str:
    lesson = ch.get("lesson", {})
    l_title = js_string(lesson.get("title", ""))
    l_short = js_string(lesson.get("short", ch.get("year", "")))
    l_tag = js_string(lesson.get("tagline", ""))
    l_tags = js_string(lesson.get("tags", ""))
    year = js_string(ch.get("year", "IMPORTED"))
    accent = js_string(ch.get("accent", "teal"))

    cases_lines = "\n".join(emit_case(c) for c in ch.get("cases", []))

    return (
        f"  {START}\n"
        f"  {{ year: {year}, accent: {accent},\n"
        f"    lesson: {{ title:{l_title}, short:{l_short}, tagline:{l_tag}, tags:{l_tags} }},\n"
        f"    cases: [\n"
        f"{cases_lines}\n"
        f"    ] }},\n"
        f"  {END}"
    )


def splice(html: str, chapter_block: str) -> str:
    if START in html and END in html:
        # Replace existing import block.
        start_idx = html.index(START)
        line_start = html.rfind("\n", 0, start_idx) + 1
        end_idx = html.index(END) + len(END)
        return html[:line_start] + chapter_block + html[end_idx:]

    # Insert before the closing `];` of SECTIONS.
    open_match = SECTIONS_OPEN.search(html)
    if not open_match:
        raise RuntimeError("Could not find `const SECTIONS = [` in HTML.")
    # Find the first `];` after SECTIONS opens.
    for m in SECTIONS_CLOSE.finditer(html, open_match.end()):
        insert_at = m.start()
        return html[:insert_at] + chapter_block + "\n" + html[insert_at:]
    raise RuntimeError("Could not find closing `];` of SECTIONS array.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chapter", type=Path, help="Imported chapter JSON (from import_pptx.py).")
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    chapter = json.loads(args.chapter.read_text())
    block = emit_chapter(chapter)
    html = args.html.read_text()
    patched = splice(html, block)

    if args.dry_run:
        print(block)
        return 0

    args.html.write_text(patched)
    print(f"[done] Merged {len(chapter.get('cases', []))} cases into {args.html.name}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
