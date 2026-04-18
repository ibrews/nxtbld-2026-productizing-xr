"""Merge multiple Spatial Deck sources (HTML / chapter JSON / SECTIONS JSON)
into a single SECTIONS-shape JSON, flagging conflicts for human review.

This is the *mechanical* half of the roadmap item "multi-deck merge":
- Pure-Python concatenation
- Conflict detection: duplicate chapter years, duplicate case titles,
  near-duplicate cases (Jaccard over bullet tokens)
- Deterministic output order (by source, preserving each source's order)

Editorial ordering + overlap resolution is a Claude job, not a fleet job —
local models have no taste for narrative structure. This tool gives Claude
(or you) a clean diffable merged draft to edit.

Usage:
    python3 tools/merge_decks.py index.html other.html tools/chapter.json
    python3 tools/merge_decks.py a.html b.html --out /tmp/merged.json
    python3 tools/merge_decks.py a.html b.html --drop-duplicates
    python3 tools/merge_decks.py a.html b.html --prefix-year   # prefix with source filename

Output JSON:
    {
      "sections": [...],       // SECTIONS array, ready for merge_sections.py
      "conflicts": [...],      // human-readable list
      "sources":   [...]       // filename + chapter count per input
    }
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lint_deck import extract_sections  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

SAFE = re.compile(r"[^a-zA-Z0-9]+")
WORD = re.compile(r"[a-z0-9]+")
STOPWORDS = {"the", "a", "an", "of", "to", "in", "and", "or", "for", "is", "it",
             "on", "at", "by", "with", "that", "this", "as", "are", "was", "be"}


def load(path: Path) -> list[dict]:
    if path.suffix == ".html":
        return extract_sections(path)
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "cases" in data:
        return [data]
    raise ValueError(f"Don't know how to interpret {path}")


def _tokens(text: str) -> set[str]:
    return {w for w in WORD.findall((text or "").lower()) if w not in STOPWORDS and len(w) > 2}


def _case_tokens(c: dict) -> set[str]:
    parts = [c.get("title", ""), c.get("subtitle", "")]
    parts.extend(c.get("bullets") or [])
    return _tokens(" ".join(str(p) for p in parts))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def merge(sources: list[tuple[Path, list[dict]]], *,
          drop_duplicates: bool, prefix_year: bool,
          similarity_threshold: float = 0.55) -> dict:
    conflicts: list[str] = []
    all_chapters: list[dict] = []

    # Track seen keys for duplicate detection. Keyed by (source index, path)
    # so the "same file passed twice" case still surfaces collisions.
    seen_years: dict[str, str] = {}
    seen_titles: dict[str, tuple[str, dict]] = {}
    case_fingerprints: list[tuple[str, str, set[str]]] = []

    for src_idx, (path, sections) in enumerate(sources):
        src = f"{path.name}#{src_idx}" if sum(1 for p, _ in sources if p.name == path.name) > 1 else path.name
        src_stem = SAFE.sub("-", path.stem).strip("-").lower() or "src"
        for ch in sections:
            ch = json.loads(json.dumps(ch))  # deep copy
            year = (ch.get("year") or "").strip() or f"#{len(all_chapters)}"

            if prefix_year:
                ch["year"] = f"{src_stem}/{year}"
            # Conflict: same year across sources.
            if year in seen_years and seen_years[year] != src:
                conflicts.append(
                    f"[year collision] '{year}' appears in both {seen_years[year]} and {src}"
                    + (" — kept both (prefix-year)" if prefix_year else " — kept both as-is")
                )
            seen_years.setdefault(year, src)

            kept_cases = []
            for c in ch.get("cases") or []:
                title = (c.get("title") or "").strip()
                key = title.lower()
                tokens = _case_tokens(c)

                # Exact title match in another source → duplicate.
                if key and key in seen_titles and seen_titles[key][0] != src:
                    prev_src, _ = seen_titles[key]
                    conflicts.append(f"[duplicate case title] '{title}' in {prev_src} and {src}")
                    if drop_duplicates:
                        continue

                # Near-duplicate by content overlap → flag, but keep unless drop.
                for fp_src, fp_title, fp_tokens in case_fingerprints:
                    if fp_src == src:
                        continue
                    sim = _jaccard(tokens, fp_tokens)
                    if sim >= similarity_threshold:
                        conflicts.append(
                            f"[similar cases {sim:.0%}] '{fp_title}' ({fp_src}) ≈ '{title}' ({src})"
                        )
                        break  # one warning per case is enough

                seen_titles.setdefault(key, (src, c))
                case_fingerprints.append((src, title, tokens))
                kept_cases.append(c)

            ch["cases"] = kept_cases
            all_chapters.append(ch)

    return {
        "sections":  all_chapters,
        "conflicts": conflicts,
        "sources":   [{"file": str(p), "chapters": len(s)} for p, s in sources],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=None, help="write SECTIONS JSON")
    ap.add_argument("--drop-duplicates", action="store_true",
                    help="silently drop cases with duplicate titles (default: keep both + flag)")
    ap.add_argument("--prefix-year", action="store_true",
                    help="prefix each chapter's year with the source filename to avoid year collisions")
    ap.add_argument("--threshold", type=float, default=0.55,
                    help="Jaccard similarity threshold for near-duplicate detection (0-1)")
    args = ap.parse_args()

    loaded: list[tuple[Path, list[dict]]] = []
    for p in args.sources:
        if not p.exists():
            print(f"ERROR: {p} not found", file=sys.stderr)
            return 2
        loaded.append((p, load(p)))

    result = merge(loaded, drop_duplicates=args.drop_duplicates,
                   prefix_year=args.prefix_year, similarity_threshold=args.threshold)

    n_ch = len(result["sections"])
    n_cases = sum(len(ch.get("cases") or []) for ch in result["sections"])
    print(f"[merge] {len(loaded)} source(s) → {n_ch} chapters / {n_cases} cases"
          f" · {len(result['conflicts'])} conflicts flagged", file=sys.stderr)
    for c in result["conflicts"]:
        print(f"  {c}", file=sys.stderr)

    if args.out:
        args.out.write_text(json.dumps(result["sections"], indent=2, ensure_ascii=False))
        print(f"[done] Wrote {args.out}", file=sys.stderr)
        if result["conflicts"]:
            report = args.out.with_suffix(".conflicts.md")
            report.write_text("# Merge conflicts\n\n" + "\n".join(f"- {c}" for c in result["conflicts"]) + "\n")
            print(f"[done] Wrote {report}", file=sys.stderr)
    else:
        sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
