"""Diff two Spatial Deck SECTIONS arrays — tells you what changed between
two HTML files (or between HTML and a chapter JSON), as a readable report.

Typical uses:
  - Before re-running an importer, snapshot the current deck, then after
    the merge run this to see what actually moved.
  - Fork / template pull: `git checkout template/main -- index.html` into
    /tmp, then diff to preview the merge.
  - Pair with `estimate_timing.py` to see if a revision changed total length.

Diff semantics:
  - Chapters matched by `year` (stable label); falls back to positional.
  - Cases matched by `title` within a chapter; duplicates disambiguated
    positionally. Unmatched cases are flagged as added/removed.
  - Field-level diffs reported for title, subtitle, img, bullets, notes.

Usage:
    python3 tools/diff_decks.py old.html new.html
    python3 tools/diff_decks.py index.html tools/imported-foo.json
    python3 tools/diff_decks.py a.html b.html --json
"""
from __future__ import annotations
import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lint_deck import extract_sections  # node-backed for .html

REPO_ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> list[dict]:
    """Accepts either an HTML file (extracts SECTIONS) or a chapter JSON
    (returns [chapter]) or a SECTIONS-JSON dump."""
    if path.suffix == ".html":
        return extract_sections(path)
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data  # already SECTIONS-shape
    if isinstance(data, dict) and "cases" in data:
        return [data]  # single chapter
    raise ValueError(f"Don't know how to interpret {path} (expected SECTIONS list or chapter dict)")


def _chapter_key(ch: dict, idx: int) -> str:
    return str(ch.get("year") or f"#{idx}")


def _case_key(c: dict) -> str:
    return (c.get("title") or "").strip().lower()


def pair_by_key(old: list[dict], new: list[dict], keyfn) -> list[tuple[dict | None, dict | None]]:
    """Greedy match by key; unmatched items pair with None on the other side.
    Items with duplicate keys pair positionally within the duplicate group."""
    from collections import defaultdict
    old_by: dict[str, list[dict]] = defaultdict(list)
    new_by: dict[str, list[dict]] = defaultdict(list)
    for item in old:
        old_by[keyfn(item)].append(item)
    for item in new:
        new_by[keyfn(item)].append(item)

    paired: list[tuple[dict | None, dict | None]] = []
    # Preserve new-side order: iterate old keys first to emit removed-before-added
    # roughly in stable order.
    all_keys = list(dict.fromkeys(list(old_by.keys()) + list(new_by.keys())))
    for k in all_keys:
        o_list = old_by.get(k, [])
        n_list = new_by.get(k, [])
        for i in range(max(len(o_list), len(n_list))):
            o = o_list[i] if i < len(o_list) else None
            n = n_list[i] if i < len(n_list) else None
            paired.append((o, n))
    return paired


def diff_strings(old: str, new: str, name: str) -> list[str]:
    old, new = (old or "").strip(), (new or "").strip()
    if old == new:
        return []
    if not old:
        return [f"+ {name}: {new[:120]!r}"]
    if not new:
        return [f"- {name}: {old[:120]!r}"]
    return [f"~ {name}: {old[:60]!r} → {new[:60]!r}"]


def diff_bullets(old: list, new: list) -> list[str]:
    old = [str(b) for b in (old or [])]
    new = [str(b) for b in (new or [])]
    if old == new:
        return []
    lines: list[str] = []
    sm = difflib.SequenceMatcher(a=old, b=new)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            for b in old[i1:i2]:
                lines.append(f"  - bullet removed: {b[:100]!r}")
        elif tag == "insert":
            for b in new[j1:j2]:
                lines.append(f"  + bullet added:   {b[:100]!r}")
        elif tag == "replace":
            # Pair 1-to-1 when lengths match; otherwise delete-then-insert.
            if (i2 - i1) == (j2 - j1):
                for bo, bn in zip(old[i1:i2], new[j1:j2]):
                    lines.append(f"  ~ bullet changed: {bo[:50]!r} → {bn[:50]!r}")
            else:
                for b in old[i1:i2]:
                    lines.append(f"  - bullet removed: {b[:100]!r}")
                for b in new[j1:j2]:
                    lines.append(f"  + bullet added:   {b[:100]!r}")
    return lines


def diff_case(old: dict | None, new: dict | None) -> list[str]:
    if old is None and new is None:
        return []
    if old is None:
        return [f"+ CASE ADDED: {(new.get('title') or '')[:60]!r}"]
    if new is None:
        return [f"- CASE REMOVED: {(old.get('title') or '')[:60]!r}"]
    changes: list[str] = []
    changes += diff_strings(old.get("title") or "", new.get("title") or "", "title")
    changes += diff_strings(old.get("subtitle") or "", new.get("subtitle") or "", "subtitle")
    changes += diff_strings(old.get("img") or "", new.get("img") or "", "img")
    changes += diff_strings(old.get("notes") or "", new.get("notes") or "", "notes")
    changes += diff_bullets(old.get("bullets") or [], new.get("bullets") or [])
    if changes:
        return [f"~ CASE: {(new.get('title') or old.get('title') or '')[:60]!r}"] + [f"  {c}" for c in changes]
    return []


def diff_chapter(old: dict | None, new: dict | None) -> list[str]:
    if old is None and new is None:
        return []
    if old is None:
        return [f"+ CHAPTER ADDED: {new.get('year', '?')}"]
    if new is None:
        return [f"- CHAPTER REMOVED: {old.get('year', '?')}"]
    out = []
    # Lesson-level fields.
    old_lesson = old.get("lesson") or {}
    new_lesson = new.get("lesson") or {}
    for key in ("title", "tagline", "short", "tags", "notes"):
        out += diff_strings(old_lesson.get(key) or "", new_lesson.get(key) or "", f"lesson.{key}")
    out += diff_strings(old.get("accent") or "", new.get("accent") or "", "accent")

    # Case-level pairing by title.
    pairs = pair_by_key(old.get("cases") or [], new.get("cases") or [], _case_key)
    for o, n in pairs:
        out += diff_case(o, n)

    if out:
        return [f"~ CHAPTER: year={new.get('year', old.get('year', '?'))}"] + [f"  {line}" for line in out]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old", type=Path)
    ap.add_argument("new", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    old_sections = load(args.old)
    new_sections = load(args.new)

    pairs = pair_by_key(old_sections, new_sections,
                        lambda ch: _chapter_key(ch, 0))  # year key
    all_changes: list[str] = []
    for o, n in pairs:
        all_changes += diff_chapter(o, n)

    totals = {
        "chapters_added":   sum(1 for line in all_changes if line.startswith("+ CHAPTER")),
        "chapters_removed": sum(1 for line in all_changes if line.startswith("- CHAPTER")),
        "cases_added":      sum(1 for line in all_changes if line.strip().startswith("+ CASE ADDED")),
        "cases_removed":    sum(1 for line in all_changes if line.strip().startswith("- CASE REMOVED")),
        "cases_changed":    sum(1 for line in all_changes if line.strip().startswith("~ CASE")),
    }

    if args.json:
        sys.stdout.write(json.dumps({"totals": totals, "lines": all_changes}, indent=2) + "\n")
        return 0

    header = f"# Deck diff: {args.old.name} → {args.new.name}"
    print(header)
    print()
    print(f"**{totals['cases_changed']} cases changed · "
          f"{totals['cases_added']} added · {totals['cases_removed']} removed · "
          f"{totals['chapters_added']} chapters added · {totals['chapters_removed']} chapters removed**")
    print()
    if not all_changes:
        print("_No differences._")
        return 0
    for line in all_changes:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
