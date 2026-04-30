#!/usr/bin/env python3
"""
import_fmx_deck.py — Import an FMX-format deck folder into Spatial Deck.

The FMX format differs from the per-slide KB format (handled by
import_kb_deck.py): SECTIONS.json is *already* a complete Spatial Deck
SECTIONS array (year, accent, lesson{...}, cases[...]), and a single
slides.md holds the editorial copy for cover / intro / question / bonus
/ close slides plus per-section speaker notes. The work this importer
does is mostly inlining: drop SECTIONS into the template, optionally
apply theme-overrides.css, and override the cover title/subtitle.

CLI:
  python3 tools/import_fmx_deck.py <deck_dir> --out <out.html>
                                   [--title "..."] [--subtitle "..."]
                                   [--template /path/to/index.html]

Conventions:
  * <deck_dir>/SECTIONS.json must be a JSON array in Spatial Deck's
    SECTIONS shape. Notes already inside lesson/case objects are picked
    up automatically by the template's presenter popup (Shift+N).
  * <deck_dir>/slides.md is read for cover/intro copy. If not present,
    the existing template cover is preserved.
  * <deck_dir>/theme-overrides.css, if present, is appended to <head>.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def find_sections_array(html: str) -> tuple[int, int]:
    needle = "const SECTIONS"
    start = html.find(needle)
    if start < 0:
        raise RuntimeError("Could not find 'const SECTIONS' in template.")
    open_bracket = html.find("[", start)
    if open_bracket < 0:
        raise RuntimeError("Could not find opening '[' for SECTIONS.")
    depth = 0
    i = open_bracket
    in_str: str | None = None
    escape = False
    while i < len(html):
        ch = html[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
        else:
            if ch in ("'", '"', "`"):
                in_str = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    j = i + 1
                    while j < len(html) and html[j] in " \t\r\n":
                        j += 1
                    if j < len(html) and html[j] == ";":
                        return start, j + 1
                    return start, i + 1
        i += 1
    raise RuntimeError("Unterminated SECTIONS array in template.")


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


COVER_HEADING_RE = re.compile(
    r"^##\s+0\.\s+Cover\s*$(.*?)(?=^##\s+\d|\Z)",
    re.DOTALL | re.MULTILINE,
)
BIG_TEXT_RE = re.compile(r"\*\*Big text:\*\*\s*\n((?:>.*\n?)+)", re.MULTILINE)
SUB_RE = re.compile(r"\*\*Sub:?\*\*\s*([^\n]+(?:\n(?!\*\*|\#|---).+)*)", re.MULTILINE)


def parse_cover_from_slides_md(slides_md: str) -> dict:
    """Extract cover title (first H1-style block) and subtitle from slides.md.

    Returns {} on any miss — caller falls back to manifest title / template.
    """
    out: dict[str, str] = {}
    m = COVER_HEADING_RE.search(slides_md)
    if not m:
        return out
    block = m.group(1)
    bm = BIG_TEXT_RE.search(block)
    if bm:
        big = bm.group(1)
        # Strip leading "> " from each line; first nonblank line = title head,
        # remaining lines join with <br>
        lines = [
            ln.lstrip("> ").strip()
            for ln in big.splitlines()
            if ln.strip().lstrip(">").strip()
        ]
        if lines:
            out["title"] = "<br>".join(lines)
    sm = SUB_RE.search(block)
    if sm:
        sub = sm.group(1).strip()
        # Drop trailing bullet/blank lines that may have been pulled in
        sub = re.sub(r"\s+", " ", sub)
        out["subtitle"] = sub
    return out


def build_sections_js(sections: list) -> str:
    payload = json.dumps(sections, ensure_ascii=False, indent=2)
    return f"const SECTIONS = {payload};"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("deck_dir", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--title", default=None,
                    help="Override <title> tag (defaults to cover title)")
    ap.add_argument("--subtitle", default=None,
                    help="Override cover subtitle")
    ap.add_argument("--template", type=Path, default=None,
                    help="Spatial Deck template index.html "
                         "(defaults to repo's index.html)")
    args = ap.parse_args()

    deck_dir: Path = args.deck_dir.resolve()
    if not deck_dir.is_dir():
        print(f"error: deck_dir not found: {deck_dir}", file=sys.stderr)
        return 2

    sections_path = deck_dir / "SECTIONS.json"
    if not sections_path.is_file():
        print(f"error: missing SECTIONS.json in {deck_dir}", file=sys.stderr)
        return 2
    sections = json.loads(sections_path.read_text(encoding="utf-8"))
    if not isinstance(sections, list):
        print("error: SECTIONS.json must be a JSON array (FMX format)",
              file=sys.stderr)
        return 2

    slides_md_path = deck_dir / "slides.md"
    cover_info: dict[str, str] = {}
    if slides_md_path.is_file():
        cover_info = parse_cover_from_slides_md(
            slides_md_path.read_text(encoding="utf-8"))

    template_path: Path = (
        args.template.resolve() if args.template
        else (Path(__file__).resolve().parent.parent / "index.html")
    )
    if not template_path.is_file():
        print(f"error: template not found: {template_path}", file=sys.stderr)
        return 2
    html = template_path.read_text(encoding="utf-8")

    # 1. Replace SECTIONS array
    s, e = find_sections_array(html)
    html = html[:s] + build_sections_js(sections) + html[e:]

    # 2. Override <title>
    cover_title = cover_info.get("title") or ""
    cover_subtitle = args.subtitle or cover_info.get("subtitle") or ""
    page_title = args.title or cover_title.replace("<br>", " — ") or deck_dir.name
    html = re.sub(
        r"<title>[^<]*</title>",
        f"<title>{_html_escape(page_title)}</title>",
        html, count=1,
    )

    # 3. Override cover talk-title (multi-line via <br>)
    if cover_title:
        # Split on <br> for HTML-escaping each segment, then rejoin
        parts = [_html_escape(p) for p in cover_title.split("<br>")]
        html_title = "<br>".join(parts)
        html = re.sub(
            r'(<h1 class="talk-title">)[\s\S]*?(</h1>)',
            lambda m: f"{m.group(1)}{html_title}{m.group(2)}",
            html, count=1,
        )

    # 4. Override cover subtitle
    if cover_subtitle:
        html = re.sub(
            r'(<p class="talk-subtitle">)[^<]*(</p>)',
            lambda m: f"{m.group(1)}{_html_escape(cover_subtitle)}{m.group(2)}",
            html, count=1,
        )

    # 5. Append theme-overrides.css if present
    theme_path = deck_dir / "theme-overrides.css"
    if theme_path.is_file():
        css = theme_path.read_text(encoding="utf-8")
        inject = (
            f'<style id="fmx-theme-overrides">\n/* from {theme_path.name} */\n'
            f"{css}\n</style>\n"
        )
        html = html.replace("</head>", inject + "</head>", 1)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")

    total_slides = sum(1 + len(sec.get("cases", [])) for sec in sections)
    variant = deck_dir.name
    extras = []
    if theme_path.is_file():
        extras.append("theme-overrides applied")
    if cover_title:
        extras.append("cover title set")
    extras_s = f" ({', '.join(extras)})" if extras else ""
    print(f"[ok] fmx variant={variant}  sections={len(sections)}  "
          f"slides={total_slides}  -> {args.out}{extras_s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
