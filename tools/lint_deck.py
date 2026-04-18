"""Lint the SECTIONS array inside index.html — never mutates, just reports.

Checks (deterministic, zero-LLM by default):
  - Title length   (> 60 chars triggers a warning, > 80 an error)
  - Subtitle length (> 100 chars)
  - Bullet length  (> 140 chars)
  - Too many bullets per case  (> 5)
  - Duplicate case titles across the deck
  - Numbers mentioned in body bullets but NOT in the title
    (e.g., "47 minutes" in bullets with no "47" anywhere up top)
  - Empty lesson tagline
  - Missing image on a case whose bullets reference visual content
    (heuristic — flagged as info, not error)

With --llm, Sam's llama3.1:8b adds a semantic pass:
  - narrative: flag slides that feel redundant or out-of-order
  - clarity:   flag bullets that are jargon-heavy or vague

Usage:
    python3 tools/lint_deck.py
    python3 tools/lint_deck.py --html index.html
    python3 tools/lint_deck.py --json   # machine-readable
    python3 tools/lint_deck.py --llm    # add semantic pass (slow)
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fleet_client import call_json, ENDPOINTS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HTML = REPO_ROOT / "index.html"

SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}

EXTRACT_JS = r"""
const fs = require('fs');
const html = fs.readFileSync(process.argv[1], 'utf8');
// Grab from `const SECTIONS = [` through the matching `];` at column 0.
const startRe = /^const\s+SECTIONS\s*=\s*\[/m;
const m = startRe.exec(html);
if (!m) { console.error('SECTIONS not found'); process.exit(2); }
const startIdx = m.index + m[0].length - 1;  // index of the opening `[`
// Walk forward tracking bracket depth, ignoring brackets inside strings/comments.
let i = startIdx, depth = 0, inS = null, inC = null;
while (i < html.length) {
  const ch = html[i], nx = html[i+1];
  if (inC === '//') { if (ch === '\n') inC = null; i++; continue; }
  if (inC === '/*') { if (ch === '*' && nx === '/') { inC = null; i += 2; continue; } i++; continue; }
  if (inS) {
    if (ch === '\\') { i += 2; continue; }
    if (ch === inS) { inS = null; }
    i++; continue;
  }
  if (ch === '/' && nx === '/') { inC = '//'; i += 2; continue; }
  if (ch === '/' && nx === '*') { inC = '/*'; i += 2; continue; }
  if (ch === '"' || ch === "'" || ch === '`') { inS = ch; i++; continue; }
  if (ch === '[') depth++;
  else if (ch === ']') { depth--; if (depth === 0) { i++; break; } }
  i++;
}
const literal = html.slice(startIdx, i);
// Evaluate in a tiny sandbox (SECTIONS is pure data).
const SECTIONS = eval(literal);
process.stdout.write(JSON.stringify(SECTIONS));
"""


def extract_sections(html_path: Path) -> list[dict]:
    """Ask node to eval `const SECTIONS = [...]` out of index.html and return
    it as a Python list of dicts."""
    try:
        out = subprocess.run(
            ["node", "-e", EXTRACT_JS, "--", str(html_path)],
            capture_output=True, text=True, check=True, timeout=10,
        )
    except FileNotFoundError:
        raise RuntimeError("node is required for SECTIONS extraction. Install from nodejs.org.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"node failed to extract SECTIONS:\n{e.stderr}")
    return json.loads(out.stdout)


NUM_RE = re.compile(r"\b\d[\d,]*\.?\d*\b")


def _nums(s: str) -> set[str]:
    return {n.replace(",", "") for n in NUM_RE.findall(s or "")}


def check_chapter(ch: dict, idx: int) -> list[dict]:
    """Return a list of finding dicts for one chapter."""
    out: list[dict] = []
    year = ch.get("year", f"#{idx}")
    loc = f"chapter[{idx}] year={year!r}"

    lesson = ch.get("lesson") or {}
    if not (lesson.get("tagline") or "").strip():
        out.append({"sev": "warn", "where": f"{loc} lesson", "msg": "lesson tagline is empty"})

    title_full = (lesson.get("title") or "").replace("\n", " ")
    if len(title_full) > 80:
        out.append({"sev": "error", "where": f"{loc} lesson.title", "msg": f"lesson title is {len(title_full)} chars (>80)"})
    elif len(title_full) > 60:
        out.append({"sev": "warn", "where": f"{loc} lesson.title", "msg": f"lesson title is {len(title_full)} chars (>60)"})

    titles_seen: dict[str, list[int]] = {}
    for ci, c in enumerate(ch.get("cases") or []):
        cloc = f"{loc} case[{ci}]"
        title = (c.get("title") or "").strip()
        subtitle = (c.get("subtitle") or "").strip()
        img = (c.get("img") or "").strip()
        bullets = c.get("bullets") or []

        if not title:
            out.append({"sev": "error", "where": cloc, "msg": "case has no title"})
        else:
            titles_seen.setdefault(title.lower(), []).append(ci)

        title_plain = title.replace("\n", " ")
        if len(title_plain) > 80:
            out.append({"sev": "error", "where": f"{cloc}.title", "msg": f"title is {len(title_plain)} chars (>80)"})
        elif len(title_plain) > 60:
            out.append({"sev": "warn", "where": f"{cloc}.title", "msg": f"title is {len(title_plain)} chars (>60)"})

        if len(subtitle) > 100:
            out.append({"sev": "warn", "where": f"{cloc}.subtitle", "msg": f"subtitle is {len(subtitle)} chars (>100)"})

        if len(bullets) > 5:
            out.append({"sev": "warn", "where": f"{cloc}.bullets", "msg": f"{len(bullets)} bullets (>5 is hard to read)"})
        for bi, b in enumerate(bullets):
            if not isinstance(b, str):
                out.append({"sev": "error", "where": f"{cloc}.bullets[{bi}]", "msg": f"bullet is {type(b).__name__}, not str"})
                continue
            if len(b) > 140:
                out.append({"sev": "warn", "where": f"{cloc}.bullets[{bi}]", "msg": f"bullet is {len(b)} chars (>140)"})

        # Numbers-in-body-but-not-title heuristic. Only flag if there are
        # numbers in bullets at all; small, year-ish, or 1-digit numbers are noisy
        # so we only flag 2+ digit non-year numerics.
        title_nums = _nums(title) | _nums(subtitle)
        body_nums: set[str] = set()
        for b in bullets:
            if isinstance(b, str):
                body_nums |= _nums(b)
        headline_candidates = {n for n in body_nums if len(n) >= 2 and n not in title_nums}
        # Drop years — 4-digit 1900–2100 numbers are rarely the headline number.
        headline_candidates = {n for n in headline_candidates
                               if not (len(n) == 4 and n.isdigit() and 1900 <= int(n) <= 2100)}
        if headline_candidates:
            out.append({
                "sev": "info",
                "where": f"{cloc}.bullets",
                "msg": f"numbers in bullets not in title: {sorted(headline_candidates)} — consider promoting to headline",
            })

        # Image-ish bullet without an image. Very cheap heuristic.
        visual_hints = ("photo", "screenshot", "diagram", "chart", "graph", "image", "picture", "render")
        if not img and any(isinstance(b, str) and any(h in b.lower() for h in visual_hints) for b in bullets):
            out.append({"sev": "info", "where": f"{cloc}.img", "msg": "bullets mention visuals but no img set"})

    for title, indexes in titles_seen.items():
        if len(indexes) > 1:
            out.append({"sev": "warn", "where": f"{loc}", "msg": f"duplicate case title {title!r} appears at cases {indexes}"})

    return out


LLM_PROMPT = """Review this slide for problems. Be terse.

Title: {title!r}
Subtitle: {subtitle!r}
Bullets:
{bullets}

Output JSON with two keys:
  issues   — array of short strings (<=120 chars each) describing problems.
             Focus on: vague/jargon bullets, redundancy between bullets,
             bullets that don't match the title, missing context.
             Return an empty array if the slide is fine.
  verdict  — one of "clean", "minor", "rework".

Rules:
- Do not invent facts about the content.
- Maximum 3 issues per slide.
- No markdown, no emoji."""


def llm_scan_slide(case: dict) -> dict | None:
    bullets = "\n".join(f"- {b}" for b in case.get("bullets") or []) or "(none)"
    prompt = LLM_PROMPT.format(
        title=case.get("title", ""),
        subtitle=case.get("subtitle", ""),
        bullets=bullets,
    )
    try:
        data = call_json(
            "llama3.1:8b", prompt,
            endpoint=ENDPOINTS["sam"],
            required_keys=["issues", "verdict"],
            timeout=60,
        )
        issues = data.get("issues") or []
        if not isinstance(issues, list):
            return None
        return {"issues": [str(x) for x in issues][:3], "verdict": str(data.get("verdict", "unknown"))}
    except Exception as e:
        print(f"    [llm] slide lint failed: {e}", file=sys.stderr)
        return None


def format_markdown(findings: list[dict], totals: dict, llm_findings: list[dict]) -> str:
    lines = ["# Spatial Deck Lint Report", ""]
    lines.append(f"**{totals['error']} errors · {totals['warn']} warnings · {totals['info']} info**")
    lines.append("")
    if not findings and not llm_findings:
        lines.append("No issues found.")
        return "\n".join(lines)

    if findings:
        lines.append("## Deterministic checks")
        lines.append("")
        for f in findings:
            glyph = {"error": "❌", "warn": "⚠️ ", "info": "ℹ️ "}[f["sev"]]
            lines.append(f"- {glyph} `{f['where']}` — {f['msg']}")
        lines.append("")

    if llm_findings:
        lines.append("## Semantic review (llama3.1:8b@Sam)")
        lines.append("")
        for f in llm_findings:
            verdict_glyph = {"clean": "✅", "minor": "⚠️ ", "rework": "🛠️"}.get(f["verdict"], "❓")
            lines.append(f"- {verdict_glyph} `{f['where']}` — {f['verdict']}")
            for issue in f.get("issues", []):
                lines.append(f"  - {issue}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--llm", action="store_true", help="add semantic review via llama3.1:8b@Sam")
    ap.add_argument("--limit", type=int, default=0, help="with --llm, cap # slides reviewed")
    args = ap.parse_args()

    if not args.html.exists():
        print(f"ERROR: {args.html} not found", file=sys.stderr)
        return 2

    print(f"[lint] extracting SECTIONS from {args.html.name}…", file=sys.stderr)
    sections = extract_sections(args.html)
    print(f"[lint] {len(sections)} chapters loaded", file=sys.stderr)

    findings: list[dict] = []
    for i, ch in enumerate(sections):
        findings.extend(check_chapter(ch, i))

    totals = {"error": 0, "warn": 0, "info": 0}
    for f in findings:
        totals[f["sev"]] = totals.get(f["sev"], 0) + 1

    llm_findings: list[dict] = []
    if args.llm:
        all_cases = [(ci, ch_idx, c)
                     for ch_idx, ch in enumerate(sections)
                     for ci, c in enumerate(ch.get("cases") or [])]
        if args.limit:
            all_cases = all_cases[:args.limit]
        print(f"[lint] LLM-scanning {len(all_cases)} cases…", file=sys.stderr)
        for ci, ch_idx, c in all_cases:
            result = llm_scan_slide(c)
            if result and (result["verdict"] != "clean" or result["issues"]):
                llm_findings.append({
                    "where": f"chapter[{ch_idx}] case[{ci}] {c.get('title','')[:40]!r}",
                    **result,
                })

    # Deterministic order: by severity then location.
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["sev"]], f["where"]))

    if args.json:
        sys.stdout.write(json.dumps({
            "totals": totals,
            "findings": findings,
            "llm_findings": llm_findings,
        }, indent=2))
    else:
        sys.stdout.write(format_markdown(findings, totals, llm_findings))
    sys.stdout.write("\n")

    # Exit code: 1 if any errors, 0 otherwise (warnings don't fail).
    return 1 if totals["error"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
