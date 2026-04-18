"""Estimate spoken duration per slide from the SECTIONS array.

Matches the formula used inside index.html's presenter popup:
  - Bullet-shaped notes (short phrases or "-" / "•" lines): ~20 sec each
  - Prose notes: 150 words per minute
  - No notes at all: 30 sec default
  - Case slides without notes still get a base of `30s + 10s per bullet`.

Outputs a per-slide table + total. Flags slides whose estimated duration
is outside a reasonable band (too rushed or too sparse).

With --generate, draft notes for notes-less slides via llama3.1:8b@Sam
and emit them as a JSON patch you can merge by hand (never mutates
index.html directly).

Usage:
    python3 tools/estimate_timing.py
    python3 tools/estimate_timing.py --target 20  # 20-minute talk
    python3 tools/estimate_timing.py --json
    python3 tools/estimate_timing.py --generate > notes-patch.json
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fleet_client import call_json, ENDPOINTS  # noqa: E402
from lint_deck import extract_sections  # reuse node-backed extractor

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HTML = REPO_ROOT / "index.html"

BULLET_MARK_RE = re.compile(r"^\s*[-•*]\s+", re.MULTILINE)
WORDS_RE = re.compile(r"\b[\w']+\b")

WPM_PROSE = 150
SEC_PER_BULLET = 20
SEC_DEFAULT = 30
SEC_CASE_BASE = 30
SEC_PER_CASE_BULLET = 10


def classify_notes(notes: str) -> tuple[str, int]:
    """Return ('prose'|'bullets'|'empty', estimated_seconds)."""
    if not notes or not notes.strip():
        return "empty", SEC_DEFAULT
    # Count explicit bullet markers.
    lines = [ln for ln in notes.splitlines() if ln.strip()]
    bullet_lines = [ln for ln in lines if BULLET_MARK_RE.match(ln)]
    if bullet_lines and len(bullet_lines) >= len(lines) // 2:
        return "bullets", max(SEC_DEFAULT, len(bullet_lines) * SEC_PER_BULLET)
    words = len(WORDS_RE.findall(notes))
    if words < 8:
        # Very short prose — treat as a single bullet.
        return "bullets", SEC_PER_BULLET
    return "prose", max(SEC_DEFAULT, round(words / WPM_PROSE * 60))


def estimate_case(case: dict) -> dict:
    notes = (case.get("notes") or "").strip()
    kind, secs = classify_notes(notes)
    if kind == "empty":
        # Fallback: base on bullet count on the slide itself.
        bc = len(case.get("bullets") or [])
        secs = SEC_CASE_BASE + bc * SEC_PER_CASE_BULLET
    return {
        "title": case.get("title", "").replace("\n", " ")[:60],
        "kind": kind,
        "seconds": secs,
        "words": len(WORDS_RE.findall(notes)),
        "has_notes": bool(notes),
    }


def estimate_lesson(lesson: dict) -> dict:
    notes = (lesson.get("notes") or "").strip()
    kind, secs = classify_notes(notes)
    return {
        "title": (lesson.get("title") or "").replace("\n", " ")[:60],
        "kind": kind,
        "seconds": secs,
        "words": len(WORDS_RE.findall(notes)),
        "has_notes": bool(notes),
    }


def fmt_secs(s: int) -> str:
    m, sec = divmod(int(s), 60)
    return f"{m}:{sec:02d}"


GEN_PROMPT = """Draft short speaker notes for one slide. The presenter will read these silently while the slide is up.

Slide title: {title!r}
Subtitle: {subtitle!r}
Bullets:
{bullets}

Write 2-3 bullet-style lines the presenter should hit out loud. Start each with "- ". Total length 30-80 words. Preserve numbers and proper nouns exactly. No markdown. No emoji.

Output JSON with one key:
  notes — string containing the drafted notes (with embedded newlines)."""


def generate_notes_for(case: dict) -> str | None:
    bullets = "\n".join(f"- {b}" for b in case.get("bullets") or []) or "(none)"
    prompt = GEN_PROMPT.format(
        title=case.get("title", ""),
        subtitle=case.get("subtitle", ""),
        bullets=bullets,
    )
    try:
        data = call_json(
            "llama3.1:8b", prompt,
            endpoint=ENDPOINTS["sam"],
            required_keys=["notes"],
            timeout=60,
        )
        n = data.get("notes")
        if isinstance(n, str) and n.strip():
            return n.strip()
    except Exception as e:
        print(f"    [gen] failed: {e}", file=sys.stderr)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--target", type=float, default=0.0, help="target total minutes (flag over/under)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--generate", action="store_true",
                    help="Draft notes for slides missing them (outputs a JSON patch).")
    ap.add_argument("--limit", type=int, default=0, help="with --generate, cap slides drafted")
    args = ap.parse_args()

    sections = extract_sections(args.html)

    rows: list[dict] = []
    for ch_idx, ch in enumerate(sections):
        lesson = ch.get("lesson") or {}
        if lesson:
            row = estimate_lesson(lesson)
            row["where"] = f"chapter[{ch_idx}].lesson"
            row["type"] = "lesson"
            rows.append(row)
        for ci, c in enumerate(ch.get("cases") or []):
            row = estimate_case(c)
            row["where"] = f"chapter[{ch_idx}].case[{ci}]"
            row["type"] = "case"
            rows.append(row)

    total_secs = sum(r["seconds"] for r in rows)
    missing = [r for r in rows if not r["has_notes"]]

    if args.generate:
        # Collect (chapter_idx, case_idx) pairs for notes-less cases only.
        to_draft: list[tuple[int, int, dict]] = []
        for ch_idx, ch in enumerate(sections):
            for ci, c in enumerate(ch.get("cases") or []):
                if not (c.get("notes") or "").strip():
                    to_draft.append((ch_idx, ci, c))
        if args.limit:
            to_draft = to_draft[:args.limit]
        patch = []
        print(f"[gen] drafting notes for {len(to_draft)} cases…", file=sys.stderr)
        for ch_idx, ci, c in to_draft:
            drafted = generate_notes_for(c)
            if drafted:
                patch.append({
                    "chapter": ch_idx,
                    "case": ci,
                    "title": c.get("title", ""),
                    "notes": drafted,
                })
                print(f"  ch{ch_idx}.case{ci} {c.get('title','')[:40]}: +{len(drafted)} chars", file=sys.stderr)
        sys.stdout.write(json.dumps({"patch": patch}, indent=2))
        sys.stdout.write("\n")
        return 0

    if args.json:
        sys.stdout.write(json.dumps({
            "total_seconds": total_secs,
            "total_formatted": fmt_secs(total_secs),
            "missing_notes": len(missing),
            "target_minutes": args.target,
            "rows": rows,
        }, indent=2))
        sys.stdout.write("\n")
        return 0

    # Markdown report.
    out = ["# Spatial Deck Timing Estimate", ""]
    out.append(f"**Total: {fmt_secs(total_secs)}** across {len(rows)} slides · {len(missing)} missing notes")
    if args.target:
        target_s = int(args.target * 60)
        delta = total_secs - target_s
        sign = "+" if delta >= 0 else "−"
        glyph = "🟢" if abs(delta) <= target_s * 0.10 else ("🟡" if abs(delta) <= target_s * 0.25 else "🔴")
        out.append(f"Target: {args.target:.0f} min ({fmt_secs(target_s)}) — {glyph} {sign}{fmt_secs(abs(delta))}")
    out.append("")
    out.append("| # | Where | Type | Title | Kind | Words | Duration |")
    out.append("|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        out.append(f"| {i} | `{r['where']}` | {r['type']} | {r['title']} | {r['kind']} | {r['words']} | {fmt_secs(r['seconds'])} |")
    out.append("")
    if missing:
        out.append(f"## {len(missing)} slides missing notes")
        out.append("")
        for r in missing:
            out.append(f"- `{r['where']}` — {r['title']}")
        out.append("")
        out.append("Run with `--generate` to draft notes for these via llama3.1:8b@Sam.")
    sys.stdout.write("\n".join(out))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
