"""Peer-review harness: two reviewers from DIFFERENT model families critique
the same SECTIONS / chapter, and we merge-vote the results.

Pattern we've found useful in this repo: any single reviewer is noisy, but two
reviewers from different model families have decorrelated errors — issues both
flag are high-confidence; solo flags are suggestions. See KB:
`departments/engineering/fleet-delegation-lessons.md`.

Reviewers come from any provider with valid creds (see review_providers.py):
  - ollama  (local fleet — Sam: llama3.1:8b · Archie: qwen2.5-coder:14b)
  - claude  (ANTHROPIC_API_KEY)
  - gemini  (GEMINI_API_KEY or GOOGLE_API_KEY)
  - openai  (OPENAI_API_KEY)

`--provider auto` (default) picks the best available pair, preferring the proven
ollama Sam+Archie combo if both fleet hosts are reachable, otherwise falling
back to two distinct API providers in priority order [claude, gemini, openai].

Each reviewer returns JSON of the form:
  {"issues": [{"case_title": "...", "severity": "high|med|low",
               "category": "clarity|structure|tone|fact|length",
               "note": "..."}, ...]}

Usage:
    python3 tools/peer_review.py index.html
    python3 tools/peer_review.py index.html --provider claude,gemini
    python3 tools/peer_review.py index.html --provider ollama:sam,ollama:archie
    python3 tools/peer_review.py index.html --chapter 1 --json > review.json
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lint_deck import extract_sections  # noqa: E402
from review_providers import Provider, build_pair  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

LENSES = (
    "narrative clarity, tone, pacing — is each slide doing one clear job?",
    "structural consistency — bullet parallelism, title/subtitle coherence, redundancy across cases",
)

PROMPT = """You are reviewing a Spatial Deck chapter for the author.

Your reviewing lens: {lens}

Chapter under review (JSON):
{chapter_json}

Return a JSON object with ONE key:
  issues — array of objects. Each object MUST have:
    case_title : string (exact title from input, or "" for chapter-level issue)
    severity   : "high" | "med" | "low"
    category   : "clarity" | "structure" | "tone" | "fact" | "length"
    note       : string, one short sentence (<=140 chars)

Rules:
  - Max 12 issues total. Pick the most important.
  - Do not invent facts. If a bullet is vague, say so; do not "fix" it.
  - If the chapter is genuinely clean, return {{"issues": []}}.
"""


def review_one(chapter: dict, provider: Provider, lens: str, timeout: int = 240) -> list[dict]:
    prompt = PROMPT.format(
        lens=lens,
        chapter_json=json.dumps(chapter, ensure_ascii=False, indent=2),
    )
    data = provider.review(prompt, timeout=timeout)
    issues = data.get("issues") or []
    cleaned: list[dict] = []
    for i in issues:
        if not isinstance(i, dict):
            continue
        cleaned.append({
            "case_title": str(i.get("case_title") or "").strip(),
            "severity":   str(i.get("severity") or "med").strip().lower(),
            "category":   str(i.get("category") or "clarity").strip().lower(),
            "note":       str(i.get("note") or "").strip(),
            "_by":        provider.label,
        })
    return cleaned


def merge_vote(reviews: list[list[dict]]) -> dict:
    """Bucket issues by (case_title, category) so near-duplicates across
    reviewers collapse into one row with both author tags."""
    from collections import defaultdict
    buckets: dict[tuple[str, str], dict] = {}
    for rlist in reviews:
        for r in rlist:
            key = ((r["case_title"] or "").lower(), r["category"])
            if key in buckets:
                b = buckets[key]
                if r["_by"] not in b["_by"]:
                    b["_by"].append(r["_by"])
                # Keep the harsher severity.
                order = {"high": 3, "med": 2, "low": 1}
                if order.get(r["severity"], 0) > order.get(b["severity"], 0):
                    b["severity"] = r["severity"]
                # Join notes if distinct.
                if r["note"] and r["note"] not in b["note"]:
                    b["note"] = (b["note"] + " | " + r["note"]).strip(" |")
            else:
                buckets[key] = {
                    "case_title": r["case_title"],
                    "severity":   r["severity"],
                    "category":   r["category"],
                    "note":       r["note"],
                    "_by":        [r["_by"]],
                }

    issues = list(buckets.values())
    for b in issues:
        b["confidence"] = "both" if len(b["_by"]) >= 2 else "one"

    sev_order = {"high": 0, "med": 1, "low": 2}
    issues.sort(key=lambda b: (
        b["confidence"] != "both",
        sev_order.get(b["severity"], 9),
        b["case_title"],
    ))
    return {
        "issues": issues,
        "counts": {
            "high_confidence": sum(1 for i in issues if i["confidence"] == "both"),
            "single_reviewer": sum(1 for i in issues if i["confidence"] == "one"),
            "total_raw":       sum(len(r) for r in reviews),
        },
    }


def load(path: Path) -> list[dict]:
    if path.suffix == ".html":
        return extract_sections(path)
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "cases" in data:
        return [data]
    raise ValueError(f"Don't know how to interpret {path}")


def render_markdown(chapter_label: str, merged: dict) -> list[str]:
    lines = [f"## {chapter_label}"]
    c = merged["counts"]
    lines.append(f"_{c['high_confidence']} both-flagged · {c['single_reviewer']} single-reviewer · {c['total_raw']} raw_")
    lines.append("")
    if not merged["issues"]:
        lines.append("_No issues raised._")
        return lines
    for i in merged["issues"]:
        badge = "🔴" if i["confidence"] == "both" else "🟡"
        tag = f"[{i['severity']}/{i['category']}]"
        title = i["case_title"] or "(chapter)"
        lines.append(f"- {badge} **{title}** {tag} — {i['note']}  _({', '.join(i['_by'])})_")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", type=Path, help="HTML file or chapter/SECTIONS JSON")
    ap.add_argument("--chapter", type=int, default=None, help="review only this chapter index (0-based)")
    ap.add_argument("--provider", default="auto",
                    help="auto | comma-separated pair (e.g. 'claude,gemini', 'ollama:sam,ollama:archie')")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        rev_a, rev_b = build_pair(args.provider, LENSES)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    print(f"[peer-review] reviewers: {rev_a.label} ({rev_a.family}) + {rev_b.label} ({rev_b.family})",
          file=sys.stderr)
    pair = ((rev_a, LENSES[0]), (rev_b, LENSES[1]))

    sections = load(args.source)
    if args.chapter is not None:
        if not (0 <= args.chapter < len(sections)):
            print(f"ERROR: chapter index out of range (0..{len(sections)-1})", file=sys.stderr)
            return 2
        sections = [sections[args.chapter]]

    all_results: list[dict] = []
    for i, ch in enumerate(sections):
        label = f"Chapter {i} ({ch.get('year', '?')}) — {(ch.get('lesson') or {}).get('title', '')[:60]}"
        print(f"[peer-review] {label}", file=sys.stderr)
        reviews: list[list[dict]] = []
        for prov, lens in pair:
            try:
                print(f"  {prov.label} …", file=sys.stderr)
                reviews.append(review_one(ch, prov, lens))
            except Exception as e:
                print(f"  {prov.label} failed: {e}", file=sys.stderr)
                reviews.append([])
        merged = merge_vote(reviews)
        all_results.append({"chapter_label": label, "merged": merged})

    if args.json:
        sys.stdout.write(json.dumps(all_results, indent=2, ensure_ascii=False) + "\n")
        return 0

    lines = [f"# Peer review: {args.source.name}", ""]
    for r in all_results:
        lines.extend(render_markdown(r["chapter_label"], r["merged"]))
        lines.append("")
    sys.stdout.write("\n".join(lines).rstrip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
