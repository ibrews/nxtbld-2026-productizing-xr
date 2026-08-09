# NXT BLD 2026 — Productizing XR for Architecture

**"Productizing XR for Architecture — Where Are You in the Cycle?"** — a talk by **Alex Coulombe** & **Jun** for **NXT BLD 2026**.

This repo is a [Spatial Deck](https://github.com/ibrews/spatial-deck) fork — single-file HTML, zero build, all content baked into `index.html`. Source of truth for the slides themselves is a Google Slides deck that Alex and Jun are co-editing; this repo pulls from it via [`tools/sync_gslides.py`](tools/sync_gslides.py).

> **Status:** Session 0 — sync initialized, 110 slides staged as `pending`. No slides have been implemented yet.

## Quickstart

```bash
git clone https://github.com/ibrews/nxtbld-2026-productizing-xr
cd nxtbld-2026-productizing-xr
python3 -m http.server 8080
# open http://localhost:8080
```

## Source sync

The talk content is authored in [Google Slides](https://docs.google.com/presentation/d/1cbYlmcqXFU-lgHIM-259cZyx2ircKLoz6vUopCKsxvA/edit). To re-sync after edits:

```bash
python3 tools/sync_gslides.py pull              # diff + update manifest + extract source/
python3 tools/sync_gslides.py pull --dry-run    # just show what changed
python3 tools/sync_gslides.py status --pending  # list slides still needing implementation
python3 tools/sync_gslides.py mark p47 generated   # after implementing a slide in SECTIONS
python3 tools/sync_gslides.py mark p13 locked      # protect a hand-tuned slide from auto-revert
```

The manifest at `gslides-manifest.json` is committed and tracks state (`pending` / `generated` / `locked`) per slide, keyed by the Google Slides page-id preserved in PPTX exports. See the [sync_gslides.py docstring](tools/sync_gslides.py) for the full behavior contract.

## Things to Try

1. **Open `index.html` in any browser** — you'll see the upstream Spatial Deck sample content; the NXT BLD talk slides are still being implemented from `source/slides/`.
2. **Run `python3 tools/sync_gslides.py status --pending`** — see all 110 source slides with their NOTE: directives, in deck order.
3. **Open `source/slides/004-p16.json`** — that's the "Who we are" slide; the `directives` field has the NOTE: instruction for the Alex+Jun sprite scene, and `media_refs` points at Jun's headshot in `source/media/`.
4. **Pull the latest source** with `python3 tools/sync_gslides.py pull --dry-run` — if Alex or Jun has edited the Google Slides since last sync, the diff shows exactly what moved/changed.
5. **Press `M` then drag any element in the running deck** — Spatial Deck's move mode auto-copies coords for AI handoff. Same UX as upstream.

## NOTE: directives

Slide source bodies marked `NOTE: …` are instructions to the implementer (often "generate an animation here," "side-by-side comparison," "Alex and Jun as sprites…"). The sync tool extracts them per-slide and flags slides that carry them. See `tools/sync_gslides.py status --pending` for the current set.

## Upstream

Framework: [ibrews/spatial-deck](https://github.com/ibrews/spatial-deck). To sync framework updates:

```bash
git fetch upstream
git merge upstream/main
# resolve any conflicts in index.html (SECTIONS stays yours)
```

## Related

- Companion talk: [FMX 2026 — Spatial Storytelling](https://github.com/ibrews/fmx-2026-spatial-storytelling) (Alex + David Gochfeld, "Ghosts of Performances Past").
- Original keynote that spawned the framework: [HXR 2026](https://ibrews.github.io/harvardxr-keynote/).

## Support

If you like seeing this kind of thing get built and shared, [donations are always welcome](https://www.alexcoulombepresents.com/support) — they buy hardware, render time, and the freedom to keep giving most of this away.
