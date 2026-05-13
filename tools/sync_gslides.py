#!/usr/bin/env python3
"""Sync a Spatial Deck fork against a Google Slides source — re-pull on every
edit, but only flag the slides that *actually* changed for regeneration.

Why this exists
---------------
The forks (FMX, NXT BLD, etc.) take a Google Slides source as input and turn
each slide into a Spatial Deck case with hand-tuned layouts, generated
diagrams from NOTE: directives, and embedded videos. While the deck is being
built, the source keeps evolving — new slides inserted, copy tweaked, slides
reordered. We don't want to regenerate slides that haven't changed, and we
don't want to lose hand-tuning when the source moves.

Identity is tracked by the Google Slides **page-id** preserved in the PPTX
export (shape names like ``Google Shape;54;p13`` carry a ``pXX`` page-id that
is stable across reordering — verified on the NXT BLD source at 102 of 110
slides). Slides without a recoverable page-id fall back to a content+position
hybrid key.

State machine per slide
-----------------------
    pending     — needs a human pass (new, or content changed)
    generated   — implemented in index.html SECTIONS; auto-revert to
                  ``pending`` if source content hash changes
    locked      — hand-tuned, do NOT auto-revert on source change. Reports
                  the diff but keeps state. Useful for slides you want to
                  rebuild fully on your own terms.

CLI
---
    # First-time setup in a fork
    python3 tools/sync_gslides.py init https://docs.google.com/presentation/d/<ID>/edit

    # Re-sync after the source has been edited
    python3 tools/sync_gslides.py pull
    python3 tools/sync_gslides.py pull --dry-run   # diff only, don't write

    # Mark a slide done (or lock it from auto-revert)
    python3 tools/sync_gslides.py mark p47 generated
    python3 tools/sync_gslides.py mark p13 locked

    # See the state distribution
    python3 tools/sync_gslides.py status
    python3 tools/sync_gslides.py status --pending   # just what needs work

Files produced
--------------
    gslides-manifest.json     committed — state per slide (page_id → state, hash)
    source/deck.pptx          gitignored — last-pulled PPTX
    source/slides/<page>.json committed — extracted content per slide (for git-diffable history)
    source/media/             gitignored — extracted images/videos

The export URL pattern ``…/export/pptx`` works without authentication if the
Google Slides doc is shared "anyone with the link." If it isn't, share it
that way before running, or download the PPTX manually to ``source/deck.pptx``
and re-run with ``--no-download``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = REPO_ROOT / "gslides-manifest.json"
DEFAULT_SOURCE_DIR = REPO_ROOT / "source"

# PPTX XML namespaces — the only ones we touch directly.
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
SHAPE_NAME_RE = re.compile(r"Google Shape;(\d+);([a-z0-9]+)")
SLIDES_URL_RE = re.compile(r"/presentation/d/([A-Za-z0-9_-]+)")
DIRECTIVE_RE = re.compile(r"^(NOTE|Note|note|TODO|FIX|SLIDE):", re.MULTILINE)
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


# ──────────────────────────────────────────────────────────────────────
# Google Slides URL handling
# ──────────────────────────────────────────────────────────────────────


def parse_slides_url(url_or_id: str) -> tuple[str, str]:
    """Return (canonical_url, deck_id). Accepts a full URL or a bare deck ID."""
    m = SLIDES_URL_RE.search(url_or_id)
    if m:
        deck_id = m.group(1)
    elif re.fullmatch(r"[A-Za-z0-9_-]{20,}", url_or_id):
        deck_id = url_or_id
    else:
        raise ValueError(f"Could not parse Google Slides URL or ID: {url_or_id!r}")
    canonical = f"https://docs.google.com/presentation/d/{deck_id}/edit"
    return canonical, deck_id


def export_pptx_url(deck_id: str) -> str:
    return f"https://docs.google.com/presentation/d/{deck_id}/export/pptx"


def download_pptx(deck_id: str, dest: Path) -> None:
    """Fetch the PPTX export. Requires the doc to be 'anyone with link'."""
    url = export_pptx_url(deck_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    print(f"[fetch] {url}", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "spatial-deck-sync/1"})
    with urllib.request.urlopen(req) as resp, open(tmp, "wb") as fh:
        # 64KB chunks — these decks run to 150+ MB.
        shutil.copyfileobj(resp, fh, length=64 * 1024)
        ct = resp.headers.get("content-type", "")
    if "presentationml" not in ct and "application/" not in ct:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"Unexpected content-type {ct!r} — the doc is probably not "
            "shared 'anyone with link.' Share it that way, or download "
            "the PPTX manually to source/deck.pptx and re-run with --no-download."
        )
    tmp.replace(dest)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"[fetch] wrote {dest} ({size_mb:.1f} MB)", file=sys.stderr)


# ──────────────────────────────────────────────────────────────────────
# PPTX extraction
# ──────────────────────────────────────────────────────────────────────


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def text_hash(parts: list[str]) -> str:
    """Stable hash over slide text (order-preserving, whitespace-normalized)."""
    norm = "\n".join(p.strip() for p in parts if p.strip())
    return sha1(norm.encode("utf-8"))


def list_slide_xmls(zf: zipfile.ZipFile) -> list[str]:
    """Slide XML paths in deck order. PPTX uses 1-based slideN.xml naming;
    we sort by the numeric suffix to be safe against any odd ordering."""
    names = [n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
    return sorted(names, key=lambda n: int(re.search(r"slide(\d+)\.xml", n).group(1)))


def slide_page_id(slide_xml: bytes) -> str | None:
    """Pull the Google Slides page-id from shape names like ``Google Shape;54;p13``.
    Returns the page-id (e.g. ``p13``) or None if the slide has no Google shapes."""
    matches = SHAPE_NAME_RE.findall(slide_xml.decode("utf-8", errors="replace"))
    # All shapes on a slide share the same page-id — take the first.
    return matches[0][1] if matches else None


def slide_text_runs(slide_xml: bytes) -> list[str]:
    """Extract <a:t> text runs in document order. Verbatim — preserves NOTE:
    directives and speaker copy alike."""
    root = ET.fromstring(slide_xml)
    return [el.text or "" for el in root.iter(f"{{{NS['a']}}}t")]


def slide_rels(zf: zipfile.ZipFile, slide_name: str) -> dict[str, str]:
    """Map rId → target (relative target, e.g. ``../media/image5.png``)."""
    base = Path(slide_name).name  # slide4.xml
    rels_path = f"ppt/slides/_rels/{base}.rels"
    if rels_path not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rels_path))
    out: dict[str, str] = {}
    for rel in root.findall(f"{{{RELS_NS}}}Relationship"):
        out[rel.get("Id")] = rel.get("Target") or ""
    return out


def slide_media_refs(slide_xml: bytes, rels: dict[str, str]) -> list[str]:
    """Image/video relationship targets used by this slide, in document order.

    The PPTX format uses <a:blip r:embed="rIdN"> for pictures and
    <p:videoFile r:link="rIdN"> for videos. We pull both — anything that
    points into ``ppt/media/`` counts as a media reference for hashing."""
    root = ET.fromstring(slide_xml)
    refs: list[str] = []
    for el in root.iter():
        for attr in ("{%s}embed" % NS["r"], "{%s}link" % NS["r"]):
            rid = el.get(attr)
            if rid and rid in rels:
                target = rels[rid]
                # Normalize ../media/foo.png → ppt/media/foo.png
                if target.startswith("../"):
                    target = "ppt/" + target[3:]
                if "/media/" in target:
                    refs.append(target)
    # Dedup but preserve order.
    seen: set[str] = set()
    out: list[str] = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def notes_xml_for_slide(zf: zipfile.ZipFile, slide_name: str) -> bytes | None:
    """Return the notesSlide XML bytes for the given slide, or None."""
    rels = slide_rels(zf, slide_name)
    for target in rels.values():
        if "notesSlide" in target and target.endswith(".xml"):
            notes_path = target.replace("../", "ppt/")
            if notes_path in zf.namelist():
                return zf.read(notes_path)
    return None


def speaker_notes_text(notes_xml: bytes | None) -> str:
    if not notes_xml:
        return ""
    root = ET.fromstring(notes_xml)
    parts = [el.text or "" for el in root.iter(f"{{{NS['a']}}}t")]
    return "\n".join(p for p in parts if p.strip())


def find_directives(text_runs: list[str]) -> list[str]:
    """NOTE: / TODO: / FIX: / SLIDE: lines, in order. These are instructions
    to the slide-implementer (often: 'generate an animation here')."""
    out: list[str] = []
    for run in text_runs:
        for m in DIRECTIVE_RE.finditer(run):
            line_start = run.rfind("\n", 0, m.start()) + 1
            line_end = run.find("\n", m.end())
            line = run[line_start:line_end if line_end >= 0 else len(run)].strip()
            if line:
                out.append(line)
    return out


def slide_record(zf: zipfile.ZipFile, slide_name: str, index: int) -> dict:
    """Extract everything we track for one slide."""
    slide_xml = zf.read(slide_name)
    rels = slide_rels(zf, slide_name)
    runs = slide_text_runs(slide_xml)
    media = slide_media_refs(slide_xml, rels)
    page_id = slide_page_id(slide_xml)
    notes = speaker_notes_text(notes_xml_for_slide(zf, slide_name))
    directives = find_directives(runs)
    # Title heuristic: first non-NOTE, non-empty run.
    title = next(
        (r.strip() for r in runs
         if r.strip() and not DIRECTIVE_RE.match(r.strip())),
        "",
    )
    return {
        "page_id": page_id,
        "index": index,
        "slide_xml_name": slide_name,
        "title": title[:120],
        "text_runs": runs,
        "text_hash": text_hash(runs),
        "media_refs": media,
        "media_hash": sha1("|".join(media).encode()),
        "speaker_notes": notes,
        "speaker_notes_hash": sha1(notes.encode("utf-8")),
        "directives": directives,
    }


def extract_all_slides(pptx_path: Path) -> tuple[list[dict], dict[str, bytes]]:
    """Return (slide_records, media_blobs_by_target). Media blobs are returned
    so the caller can write them out under whatever directory it wants."""
    records: list[dict] = []
    media_blobs: dict[str, bytes] = {}
    with zipfile.ZipFile(pptx_path) as zf:
        for i, name in enumerate(list_slide_xmls(zf), 1):
            records.append(slide_record(zf, name, i))
        wanted = {m for r in records for m in r["media_refs"]}
        for target in wanted:
            if target in zf.namelist():
                media_blobs[target] = zf.read(target)
    return records, media_blobs


# ──────────────────────────────────────────────────────────────────────
# Manifest IO + diff
# ──────────────────────────────────────────────────────────────────────


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def slide_key(rec: dict) -> str:
    """Identity key. Prefer page-id; fall back to text-hash + position. The
    fallback is fragile for moves but works for slides that lack Google shape
    names (the ~8/110 edge cases on the NXT BLD source)."""
    return rec["page_id"] or f"fallback:{rec['text_hash'][:12]}:{rec['index']}"


def diff_slides(old_slides: list[dict], new_records: list[dict]) -> dict:
    """Pair old manifest entries against new extraction; classify each pair.

    Returns a dict with keys: added, removed, modified, moved, unchanged,
    each a list of {old?, new?, reasons[]}."""
    old_by_key = {s["key"]: s for s in old_slides}
    new_by_key: dict[str, dict] = {}
    for rec in new_records:
        new_by_key[slide_key(rec)] = rec

    added: list[dict] = []
    removed: list[dict] = []
    modified: list[dict] = []
    moved: list[dict] = []
    unchanged: list[dict] = []

    for key, new_rec in new_by_key.items():
        old = old_by_key.get(key)
        if old is None:
            added.append({"new": new_rec, "reasons": ["new page-id"]})
            continue
        reasons: list[str] = []
        if old["text_hash"] != new_rec["text_hash"]:
            reasons.append("text changed")
        if old["media_hash"] != new_rec["media_hash"]:
            reasons.append("media changed")
        if old.get("speaker_notes_hash") != new_rec["speaker_notes_hash"]:
            reasons.append("speaker-notes changed")
        if reasons:
            modified.append({"old": old, "new": new_rec, "reasons": reasons})
        elif old["index"] != new_rec["index"]:
            moved.append({"old": old, "new": new_rec, "reasons": [
                f"position {old['index']} → {new_rec['index']}"]})
        else:
            unchanged.append({"old": old, "new": new_rec, "reasons": []})

    for key, old in old_by_key.items():
        if key not in new_by_key:
            removed.append({"old": old, "reasons": ["page-id no longer in source"]})

    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "moved": moved,
        "unchanged": unchanged,
    }


def merge_into_manifest(
    manifest: dict, new_records: list[dict], diff: dict, deck_url: str, deck_id: str
) -> dict:
    """Produce the new manifest from (old manifest + diff). State rules:

      - added            → state='pending', first_seen=now
      - modified         → state stays 'locked'; else reverts to 'pending'
      - moved/unchanged  → state preserved
      - removed          → entry kept with state='removed' (so 'locked'
                            removals don't silently disappear)
    """
    next_slides: list[dict] = []
    handled_keys: set[str] = set()

    by_key = {slide_key(r): r for r in new_records}

    # Walk in current source order so the manifest tracks deck order.
    for rec in new_records:
        key = slide_key(rec)
        handled_keys.add(key)
        old = next((m for m in manifest.get("slides", []) if m["key"] == key), None)

        # Default state: pending if new, else preserve.
        state = "pending"
        deck_target = None
        generated_at = None
        first_seen = now_iso()
        history: list[dict] = []
        manual_notes = ""

        if old:
            state = old.get("state", "pending")
            deck_target = old.get("deck_target")
            generated_at = old.get("generated_at")
            first_seen = old.get("first_seen", first_seen)
            history = list(old.get("history", []))
            manual_notes = old.get("manual_notes", "")
            # Was this in the 'modified' bucket?
            mod_hit = next((m for m in diff["modified"]
                            if slide_key(m["new"]) == key), None)
            if mod_hit and state != "locked":
                history.append({
                    "at": now_iso(),
                    "event": "auto-revert-to-pending",
                    "reasons": mod_hit["reasons"],
                })
                state = "pending"

        entry = {
            "key": key,
            "page_id": rec["page_id"],
            "index": rec["index"],
            "title": rec["title"],
            "text_hash": rec["text_hash"],
            "media_hash": rec["media_hash"],
            "speaker_notes_hash": rec["speaker_notes_hash"],
            "media_refs": rec["media_refs"],
            "has_directive": bool(rec["directives"]),
            "directives": rec["directives"],
            "state": state,
            "deck_target": deck_target,
            "generated_at": generated_at,
            "first_seen": first_seen,
            "history": history,
            "manual_notes": manual_notes,
        }
        next_slides.append(entry)

    # Preserve removed slides (don't silently drop a locked one) at the end.
    for old in manifest.get("slides", []):
        if old["key"] not in handled_keys:
            entry = dict(old)
            if entry.get("state") != "removed":
                entry.setdefault("history", []).append({
                    "at": now_iso(),
                    "event": "removed-from-source",
                    "previous_state": entry.get("state"),
                })
                entry["state"] = "removed"
            next_slides.append(entry)

    return {
        "deck_url": deck_url,
        "deck_id": deck_id,
        "last_sync": now_iso(),
        "slides": next_slides,
    }


# ──────────────────────────────────────────────────────────────────────
# Source-tree writer
# ──────────────────────────────────────────────────────────────────────


def write_source_tree(source_dir: Path, records: list[dict], media_blobs: dict[str, bytes]) -> None:
    """Write per-slide JSON + media files. Per-slide JSON is committed (for
    git-diffable history); media goes under source/media/ (gitignored)."""
    slides_dir = source_dir / "slides"
    media_dir = source_dir / "media"
    slides_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    # Per-slide JSON.
    existing = {p.name for p in slides_dir.glob("*.json")}
    written: set[str] = set()
    for rec in records:
        key = rec["page_id"] or f"fallback-{rec['text_hash'][:8]}-{rec['index']:03d}"
        out_path = slides_dir / f"{rec['index']:03d}-{key}.json"
        payload = {
            "index": rec["index"],
            "page_id": rec["page_id"],
            "title": rec["title"],
            "text_runs": rec["text_runs"],
            "directives": rec["directives"],
            "media_refs": rec["media_refs"],
            "speaker_notes": rec["speaker_notes"],
        }
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        written.add(out_path.name)

    # Prune stale per-slide JSONs (slides removed from source).
    for stale in existing - written:
        (slides_dir / stale).unlink()

    # Media — by basename, so multiple slides referencing the same image share.
    for target, blob in media_blobs.items():
        out = media_dir / Path(target).name
        out.write_bytes(blob)


# ──────────────────────────────────────────────────────────────────────
# Reporting
# ──────────────────────────────────────────────────────────────────────


def _short(s: str, n: int = 60) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def print_report(diff: dict, manifest_after: dict) -> None:
    a, r, m, mv, u = (diff["added"], diff["removed"], diff["modified"],
                      diff["moved"], diff["unchanged"])
    print(f"\n# Sync report")
    print(f"Deck: {manifest_after['deck_url']}")
    print(f"Synced: {manifest_after['last_sync']}")
    print(f"\n**{len(a)} new · {len(m)} modified · {len(r)} removed · "
          f"{len(mv)} moved · {len(u)} unchanged**")

    if a:
        print("\n## NEW (state: pending)")
        for item in a:
            n = item["new"]
            print(f"  + idx {n['index']:>3}  {n['page_id'] or '(no-id)':<6}  "
                  f"{_short(n['title'])}")
            for d in n["directives"]:
                print(f"        ↳ {_short(d, 100)}")

    if m:
        print("\n## MODIFIED")
        for item in m:
            n, o = item["new"], item["old"]
            prev = o.get("state", "?")
            new_state = "locked (kept)" if prev == "locked" else "pending (auto-reverted)"
            print(f"  ~ idx {n['index']:>3}  {n['page_id'] or '(no-id)':<6}  "
                  f"{_short(n['title'])}  [{prev} → {new_state}]")
            for reason in item["reasons"]:
                print(f"        · {reason}")
            if o.get("deck_target"):
                print(f"        deck_target: {o['deck_target']} — re-implement")

    if r:
        print("\n## REMOVED")
        for item in r:
            o = item["old"]
            prev = o.get("state", "?")
            print(f"  - was idx {o['index']:>3}  {o['page_id'] or '(no-id)':<6}  "
                  f"{_short(o['title'])}  [was {prev}]")
            if o.get("deck_target"):
                print(f"        deck_target: {o['deck_target']} — remove from SECTIONS")

    if mv:
        print("\n## MOVED (no regeneration needed)")
        for item in mv:
            n, o = item["new"], item["old"]
            print(f"  > {n['page_id'] or '(no-id)':<6}  idx {o['index']} → {n['index']}  "
                  f"{_short(n['title'])}")

    # Next-step hint.
    pending = [s for s in manifest_after["slides"] if s["state"] == "pending"]
    if pending:
        print(f"\n## Next steps")
        print(f"  {len(pending)} slide(s) in 'pending' state. After implementing "
              f"each in index.html SECTIONS, mark it done:")
        for s in pending[:5]:
            print(f"    python3 tools/sync_gslides.py mark "
                  f"{s['page_id'] or s['key']} generated")
        if len(pending) > 5:
            print(f"    ... and {len(pending) - 5} more")


# ──────────────────────────────────────────────────────────────────────
# Subcommands
# ──────────────────────────────────────────────────────────────────────


def cmd_init(args) -> int:
    url, deck_id = parse_slides_url(args.url)
    manifest_path = Path(args.manifest)
    if manifest_path.exists() and not args.force:
        print(f"ERROR: {manifest_path} already exists. Use 'pull' for ongoing sync, "
              f"or pass --force to reinit.", file=sys.stderr)
        return 2

    source_dir = Path(args.source_dir)
    pptx_path = source_dir / "deck.pptx"
    if not args.no_download:
        download_pptx(deck_id, pptx_path)
    elif not pptx_path.exists():
        print(f"ERROR: --no-download passed but {pptx_path} doesn't exist.", file=sys.stderr)
        return 2

    records, media = extract_all_slides(pptx_path)
    write_source_tree(source_dir, records, media)
    # Empty starting manifest, so every slide lands in 'added'.
    manifest = {"deck_url": url, "deck_id": deck_id, "last_sync": now_iso(), "slides": []}
    diff = diff_slides([], records)
    new_manifest = merge_into_manifest(manifest, records, diff, url, deck_id)
    save_manifest(manifest_path, new_manifest)
    print_report(diff, new_manifest)
    print(f"\n[init] wrote {manifest_path.relative_to(REPO_ROOT)}", file=sys.stderr)
    return 0


def cmd_pull(args) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: no manifest at {manifest_path}. Run `init <url>` first.",
              file=sys.stderr)
        return 2
    manifest = load_manifest(manifest_path)
    url = manifest["deck_url"]
    deck_id = manifest["deck_id"]
    source_dir = Path(args.source_dir)
    pptx_path = source_dir / "deck.pptx"

    if not args.no_download:
        download_pptx(deck_id, pptx_path)
    elif not pptx_path.exists():
        print(f"ERROR: --no-download but {pptx_path} doesn't exist.", file=sys.stderr)
        return 2

    records, media = extract_all_slides(pptx_path)
    diff = diff_slides(manifest.get("slides", []), records)
    new_manifest = merge_into_manifest(manifest, records, diff, url, deck_id)
    print_report(diff, new_manifest)

    if args.dry_run:
        print("\n[dry-run] manifest + source/ NOT updated.", file=sys.stderr)
        return 0
    write_source_tree(source_dir, records, media)
    save_manifest(manifest_path, new_manifest)
    print(f"\n[pull] manifest + source/ updated.", file=sys.stderr)
    return 0


def cmd_mark(args) -> int:
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    if not manifest:
        print(f"ERROR: no manifest at {manifest_path}.", file=sys.stderr)
        return 2

    target = args.page_id
    state = args.state
    found = None
    for entry in manifest["slides"]:
        if entry["page_id"] == target or entry["key"] == target:
            found = entry
            break
    if not found:
        print(f"ERROR: no slide with page_id or key {target!r}.", file=sys.stderr)
        return 2

    prev = found["state"]
    found["state"] = state
    if state == "generated":
        found["generated_at"] = now_iso()
        if args.deck_target:
            found["deck_target"] = args.deck_target
    if args.note:
        found["manual_notes"] = args.note
    found.setdefault("history", []).append({
        "at": now_iso(), "event": f"mark:{prev}→{state}",
        "by": "cli", "note": args.note or "",
    })
    save_manifest(manifest_path, manifest)
    print(f"[mark] {target}: {prev} → {state}", file=sys.stderr)
    return 0


def cmd_status(args) -> int:
    manifest = load_manifest(Path(args.manifest))
    if not manifest:
        print(f"ERROR: no manifest.", file=sys.stderr)
        return 2
    slides = manifest["slides"]
    counts: dict[str, int] = {}
    for s in slides:
        counts[s["state"]] = counts.get(s["state"], 0) + 1
    print(f"# Spatial Deck sync status")
    print(f"Deck: {manifest['deck_url']}")
    print(f"Last sync: {manifest['last_sync']}")
    print(f"Total slides: {len(slides)}")
    for state in ("pending", "generated", "locked", "removed"):
        if counts.get(state):
            print(f"  {state:<10} {counts[state]:>4}")
    if args.pending:
        print("\n## Pending")
        for s in slides:
            if s["state"] == "pending":
                marker = "★" if s.get("has_directive") else " "
                print(f"  {marker} idx {s['index']:>3}  "
                      f"{s['page_id'] or '(no-id)':<6}  {_short(s['title'])}")
                for d in s.get("directives", []):
                    print(f"        ↳ {_short(d, 100)}")
    return 0


# ──────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="sync_gslides",
        description="Sync a Spatial Deck fork against its Google Slides source.",
    )
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST),
                    help=f"path to manifest JSON (default: {DEFAULT_MANIFEST.name} at repo root)")
    ap.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR),
                    help="directory for extracted source artifacts (default: source/)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="first-time setup: download PPTX, build manifest")
    p_init.add_argument("url", help="Google Slides URL or deck ID")
    p_init.add_argument("--no-download", action="store_true",
                        help="use existing source/deck.pptx instead of fetching")
    p_init.add_argument("--force", action="store_true",
                        help="overwrite existing manifest")
    p_init.set_defaults(fn=cmd_init)

    p_pull = sub.add_parser("pull", help="re-fetch source, diff, update manifest")
    p_pull.add_argument("--no-download", action="store_true")
    p_pull.add_argument("--dry-run", action="store_true",
                        help="show diff without writing")
    p_pull.set_defaults(fn=cmd_pull)

    p_mark = sub.add_parser("mark", help="change a slide's state")
    p_mark.add_argument("page_id", help="page-id (e.g. p13) or full key")
    p_mark.add_argument("state", choices=["pending", "generated", "locked"])
    p_mark.add_argument("--deck-target", default=None,
                        help="optional pointer (e.g. SECTIONS index) recorded on the slide")
    p_mark.add_argument("--note", default=None, help="optional manual note")
    p_mark.set_defaults(fn=cmd_mark)

    p_status = sub.add_parser("status", help="print state distribution")
    p_status.add_argument("--pending", action="store_true",
                          help="list every pending slide with its directives")
    p_status.set_defaults(fn=cmd_status)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
