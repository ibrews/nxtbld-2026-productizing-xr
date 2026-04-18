"""Import design tokens into Spatial Deck's :root CSS block.

Accepts any text file (CSS export from Claude Design, Figma tokens JSON,
a screenshot's extracted palette, a napkin description). A local LLM on the
fleet (Sam / llama3.1:8b) normalizes it to a known schema; we validate and
splice into index.html.

Usage:
    python3 tools/import_tokens.py path/to/tokens.txt
    python3 tools/import_tokens.py path/to/tokens.txt --dry-run
    python3 tools/import_tokens.py path/to/tokens.txt --html other.html

Only the :root{...} block is modified. No LLM output is trusted verbatim —
hex colors must match /^#[0-9a-fA-F]{6}$/, font must be a string.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fleet_client import call_json, ENDPOINTS  # noqa: E402

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HTML = REPO_ROOT / "index.html"

# Maps our schema key -> CSS var name in :root.
VAR_MAP = {
    "bg":        "--bg",
    "bg_dark":   "--bg-dark",
    "text":      "--text",
    "dim":       "--dim",
    "primary":   "--primary",
    "secondary": "--secondary",
    "teal":      "--teal",
    "purple":    "--purple",
    "amber":     "--amber",
    "rose":      "--rose",
    "font":      "--font",
}

COLOR_KEYS = {"bg", "bg_dark", "text", "primary", "secondary",
              "teal", "purple", "amber", "rose"}

PROMPT = """You are normalizing a design token input into a fixed JSON schema for a presentation framework.

Input (raw, any format — CSS, JSON, prose, palette list):
---
{raw}
---

Output a JSON object with EXACTLY these keys:
  bg, bg_dark, text, dim, primary, secondary, teal, purple, amber, rose, font

Rules:
- All color values must be 6-digit hex like "#060810". No rgb(), no rgba(), no shorthand.
- "dim" is a muted text color (e.g. "#6a7080") — pick one if not specified.
- "font" is a CSS font-family string like "'Space Grotesk', system-ui, sans-serif".
- If the input only provides a partial palette, infer the rest to be visually coherent with what's given.
- bg and bg_dark should be near-identical dark tones unless the input clearly specifies light mode.
- primary/secondary are the two main accent colors. If unclear, map primary=teal, secondary=purple.
"""

SCHEMA_KEYS = list(VAR_MAP.keys())


def normalize_tokens(raw: str, *, model: str = "llama3.1:8b",
                    endpoint: str = ENDPOINTS["sam"]) -> dict:
    data = call_json(model, PROMPT.format(raw=raw), endpoint=endpoint,
                     required_keys=SCHEMA_KEYS)
    for k in COLOR_KEYS:
        v = data.get(k, "")
        if not isinstance(v, str) or not HEX.match(v):
            raise ValueError(f"Invalid hex for {k!r}: {v!r}")
    if not isinstance(data.get("font"), str) or len(data["font"]) < 3:
        raise ValueError(f"Invalid font: {data.get('font')!r}")
    return data


ROOT_BLOCK = re.compile(r":root\{([^}]*)\}")


def patch_html(html: str, tokens: dict) -> str:
    match = ROOT_BLOCK.search(html)
    if not match:
        raise RuntimeError("Could not locate :root{...} block in HTML.")
    # Normalize: ensure every declaration ends with ';' so the last var isn't
    # special-cased. We'll strip the trailing ';' before re-emitting.
    body = match.group(1).strip()
    if not body.endswith(";"):
        body += ";"

    def replace_var(body: str, var: str, value: str) -> str:
        pat = re.compile(rf"(--{re.escape(var[2:])}\s*:)([^;]*)(;)")
        if pat.search(body):
            return pat.sub(lambda m: f"{m.group(1)}{value}{m.group(3)}", body, count=1)
        return body + f"{var}:{value};"

    for key, var in VAR_MAP.items():
        replace = tokens[key]
        body = replace_var(body, var, replace)

    new_root = f":root{{{body.rstrip(';')}}}"
    return html[:match.start()] + new_root + html[match.end():]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="Token file (any text format).")
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--model", default="llama3.1:8b")
    ap.add_argument("--endpoint", default="sam", choices=list(ENDPOINTS))
    ap.add_argument("--dry-run", action="store_true",
                    help="Print normalized tokens and the patched :root block, don't write.")
    args = ap.parse_args()

    raw = args.input.read_text()
    print(f"[1/3] Normalizing tokens via {args.model}@{args.endpoint}...", file=sys.stderr)
    tokens = normalize_tokens(raw, model=args.model, endpoint=ENDPOINTS[args.endpoint])
    print(f"[2/3] Validated. Palette: {tokens['bg']} / {tokens['text']} / "
          f"primary={tokens['primary']} secondary={tokens['secondary']}", file=sys.stderr)

    html = args.html.read_text()
    patched = patch_html(html, tokens)

    if args.dry_run:
        new_root = ROOT_BLOCK.search(patched).group(0)
        print(new_root)
        return 0

    args.html.write_text(patched)
    print(f"[3/3] Wrote {args.html} ({len(patched)} bytes).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
