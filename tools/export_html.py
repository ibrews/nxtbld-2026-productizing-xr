"""Export the current SECTIONS array as a single, self-contained, static
HTML outline — one page per case, readable in any browser with zero JS.

NOT the spatial-deck runtime: that's `index.html`. This is for handoff —
a collaborator who wants to skim the deck in email, a reviewer who doesn't
want to run the interactive version, or a print-to-PDF moment.

Usage:
    python3 tools/export_html.py --out /tmp/deck.html
    python3 tools/export_html.py --chapter 1 --out /tmp/ch1.html
    python3 tools/export_html.py --html other.html --out outline.html
"""
from __future__ import annotations
import argparse
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lint_deck import extract_sections  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HTML = REPO_ROOT / "index.html"

CSS = """
:root { color-scheme: light dark; --accent-teal:#0fb3a1; --accent-purple:#7c5cff;
        --accent-amber:#f5a524; --accent-rose:#f43f7d; }
* { box-sizing: border-box; }
body { margin:0; font: 16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
       background:#0b0b10; color:#e8e8f0; }
main { max-width: 920px; margin: 0 auto; padding: 40px 28px 120px; }
header.chapter { border-top: 4px solid var(--accent); padding: 28px 0 8px; margin-top: 48px; }
header.chapter:first-of-type { margin-top: 0; }
header.chapter .year { font: 700 12px/1 ui-monospace,monospace; letter-spacing: .12em;
                       color: var(--accent); text-transform: uppercase; }
header.chapter h1 { font: 700 34px/1.15 -apple-system,sans-serif; margin: 10px 0 8px; white-space: pre-line; }
header.chapter p.tagline { color:#b8b8c8; margin: 6px 0 0; }
header.chapter .meta { font-size: 13px; color:#8888a0; margin-top: 10px; }
article.case { border-top: 1px solid #24242e; padding: 28px 0; }
article.case h2 { font: 700 22px/1.25 -apple-system,sans-serif; margin: 0 0 6px; white-space: pre-line; }
article.case p.subtitle { color:#c8c8d8; margin: 4px 0 12px; }
article.case img { max-width: 100%; height: auto; border-radius: 10px; display:block; margin: 12px 0; }
article.case ul { margin: 12px 0 0; padding-left: 22px; }
article.case ul li { margin: 4px 0; }
article.case .notes { margin-top: 14px; padding: 10px 14px; border-left: 3px solid var(--accent);
                      background: rgba(255,255,255,.03); color:#b8b8c8; font-size: 14px; white-space: pre-line; }
.iframe-note { font-size: 13px; color:#8888a0; font-style: italic; }
.counter { font: 500 12px/1 ui-monospace,monospace; color:#6a6a80; letter-spacing: .1em; }
footer { text-align: center; color:#6a6a80; font-size: 12px; margin-top: 80px; }
"""

ACCENTS = {"teal": "var(--accent-teal)", "purple": "var(--accent-purple)",
           "amber": "var(--accent-amber)", "rose": "var(--accent-rose)"}


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def render_case(c: dict, idx: int) -> list[str]:
    out = ['<article class="case">']
    out.append(f'<div class="counter">Case {idx:02d}</div>')
    out.append(f'<h2>{esc(c.get("title") or "(untitled)")}</h2>')
    subtitle = (c.get("subtitle") or "").strip()
    if subtitle:
        out.append(f'<p class="subtitle">{esc(subtitle)}</p>')
    img = (c.get("img") or "").strip()
    if img.startswith("IFRAME:"):
        out.append(f'<p class="iframe-note">↗ embeds {esc(img[7:])}</p>')
    elif img and not img.startswith("MEDIA_CYCLER"):
        alt = esc(c.get("alt") or subtitle or c.get("title") or "")
        out.append(f'<img src="{esc(img)}" alt="{alt}" loading="lazy">')
    elif img.startswith("MEDIA_CYCLER"):
        out.append('<p class="iframe-note">↗ media cycler (see interactive deck)</p>')
    bullets = c.get("bullets") or []
    if bullets:
        out.append("<ul>")
        for b in bullets:
            if isinstance(b, str) and b.strip():
                out.append(f"<li>{esc(b)}</li>")
        out.append("</ul>")
    notes = (c.get("notes") or "").strip()
    if notes:
        out.append(f'<div class="notes">{esc(notes)}</div>')
    out.append("</article>")
    return out


def render_chapter(ch: dict, ch_idx: int) -> list[str]:
    accent = ACCENTS.get((ch.get("accent") or "").strip(), ACCENTS["teal"])
    lesson = ch.get("lesson") or {}
    year = esc(ch.get("year") or f"#{ch_idx}")
    title = esc(lesson.get("title") or "")
    tagline = esc(lesson.get("tagline") or "")
    short = esc(lesson.get("short") or "")
    tags = esc(lesson.get("tags") or "")
    out = [f'<header class="chapter" style="--accent:{accent}">']
    out.append(f'<div class="year">{year}{" · " + short if short and short != year else ""}</div>')
    if title:
        out.append(f"<h1>{title}</h1>")
    if tagline:
        out.append(f'<p class="tagline">{tagline}</p>')
    if tags:
        out.append(f'<div class="meta">{tags}</div>')
    out.append("</header>")
    for i, c in enumerate(ch.get("cases") or [], 1):
        out.extend(render_case(c, i))
    return out


def render(sections: list[dict], title: str) -> str:
    body: list[str] = []
    for i, ch in enumerate(sections):
        body.extend(render_chapter(ch, i))
    total_cases = sum(len(ch.get("cases") or []) for ch in sections)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
{chr(10).join(body)}
<footer>Exported outline · {len(sections)} chapters · {total_cases} cases</footer>
</main>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--chapter", type=int, default=None)
    ap.add_argument("--title", default="Spatial Deck — Outline")
    args = ap.parse_args()

    sections = extract_sections(args.html)
    if args.chapter is not None:
        if not (0 <= args.chapter < len(sections)):
            print(f"ERROR: chapter index out of range (0..{len(sections)-1})", file=sys.stderr)
            return 2
        sections = [sections[args.chapter]]

    out = render(sections, args.title)
    if args.out:
        args.out.write_text(out)
        print(f"[done] Wrote {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
