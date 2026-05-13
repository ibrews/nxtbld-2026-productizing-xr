# NXT BLD 2026 — Productizing XR for Architecture · AI Agent Handoff

> **READ THIS FILE TOP TO BOTTOM BEFORE TOUCHING ANY SLIDES.**
> Last updated: 2026-05-13 · Session 0 (sync initialized)

---

## What this repo is

A [Spatial Deck](https://github.com/ibrews/spatial-deck) fork for **Alex Coulombe** + **Jun**'s NXT BLD 2026 talk: *"Productizing XR for Architecture — Where Are You in the Cycle?"*

Source of truth = the Google Slides deck Alex + Jun co-edit. This repo's `index.html` is what gets *implemented* from that source. They drift; the sync tool keeps them honest.

**Companion fork:** [ibrews/fmx-2026-spatial-storytelling](https://github.com/ibrews/fmx-2026-spatial-storytelling) — Alex + David Gochfeld's FMX 2026 talk. Read its `HANDOFF_PROMPT.md` and `POST_MORTEM.md` — most lessons learned there transfer here verbatim (especially the DO/DO NOT lists, the >10MB git-push gotchas, and the `MutationObserver` annotation-system pattern).

---

## Current state

- **Sync initialized.** `gslides-manifest.json` tracks all 110 source slides.
- **All slides in state `pending`.** Nothing has been implemented in `index.html` yet — the live `index.html` is still the upstream Spatial Deck sample.
- **9 slides carry `NOTE:` directives** — see `python3 tools/sync_gslides.py status --pending` for the full list.

---

## How to work in this repo

### 1. Re-sync before working

```bash
python3 tools/sync_gslides.py pull --dry-run
```

Shows what changed in the Google Slides source since last sync. If something is in the `modified` bucket and was previously `generated`, the diff reports `deck_target:` — that's the SECTIONS entry that needs re-implementation.

If the diff looks right, run it for real:

```bash
python3 tools/sync_gslides.py pull
```

### 2. Pick a `pending` slide to implement

```bash
python3 tools/sync_gslides.py status --pending
```

Lists every pending slide with its page-id, title, and any `NOTE:` directives. Slides marked with `★` carry NOTE: directives — those are the ones that need *generation* (custom diagrams, animations, sprite scenes), not just layout.

The source content for a slide lives at `source/slides/<idx>-<page-id>.json`. It contains:
- `text_runs` — every text run on the slide, verbatim
- `directives` — extracted `NOTE:` / `TODO:` / `FIX:` lines (instructions to you)
- `media_refs` — referenced images in `source/media/`
- `speaker_notes` — what Alex / Jun will say

Implement in `index.html`'s `SECTIONS` array (see Spatial Deck README for layout types: `full`, `grid`, `big`, `placed`, etc.).

### 3. Mark the slide done

```bash
python3 tools/sync_gslides.py mark <page-id> generated --deck-target "SECTIONS[2].cases[5]"
```

The `--deck-target` is a free-form hint to future-you about where the slide landed. If the source slide later changes, the diff reports this pointer so you know exactly what to update.

For hand-tuned slides that should NOT auto-revert on source edits:

```bash
python3 tools/sync_gslides.py mark <page-id> locked --note "reason"
```

---

## Talk facts

- **Alex Coulombe** — Founder · Agile Lens. NOT "XR Director" or "CEO."
- **Jun** — co-presenter. *(Last name + affiliation TBD — ask Alex before writing it on a slide.)*
- **Conference:** NXT BLD 2026.
- **Title:** "Productizing XR for Architecture"
- **Subtitle:** "Where Are You in the Cycle?"

---

## DO NOT (inherited from FMX session learnings)

1. Generate subtitles/captions unless source has direct body text or `NOTE:` directive.
2. Put speaker-notes content on the slide — notes are the script, not slide copy.
3. Use `object-fit:cover` on content images (global default is `contain`; only `grid-cover` class uses cover).
4. Label Jun's affiliation as Agile Lens unless Alex confirms.
5. Make up titles, roles, or bullets for Alex or Jun.
6. Use `window.kfOnSlideEnter` for persistent hooks — overwritten by the annotation system. Use `MutationObserver` instead.
7. Treat a <50KB full-bleed image as a real slide image — it is a video placeholder.
8. Commit files to git without running `git ls-files | xargs du -sh | sort -rh | head -20` first. Anything >10MB goes in `.gitignore` before staging.
9. **Don't manually edit `source/slides/*.json` or `gslides-manifest.json`.** Both are generated. Edit the Google Slides source and re-`pull`.
10. Remove or re-order slides without explicit instruction from Alex.

---

## DO

1. **Re-sync at the start of every session.** `python3 tools/sync_gslides.py pull --dry-run` then `pull`.
2. **Match source slide count and order.** Use the manifest's `index` field.
3. **Keep speaker notes verbatim** from `source/slides/<n>.json` → `speaker_notes`.
4. **`object-fit:contain`** for content images. `grid-cover:true` for intentional fill.
5. **`MutationObserver` on `.active` class** for slide-activation logic.
6. **Verify at 1920×1080** before declaring done.
7. **Mark slides `generated` as you implement them** — keeps the next sync diff actionable.
8. **For hand-tuned slides, lock them** so a source edit doesn't silently revert their state.
9. **For video placeholders or NOTE: directives that need custom assets** — use the spatial-deck `tools/` (e.g. `import_video_clip.py` for video trims, `gen_alt_text.py`, `extract_palette.py`).

---

## Files at a glance

```
nxtbld-2026-productizing-xr/
├── index.html                    ← The deck (currently upstream sample; rebuild for NXT BLD)
├── README.md
├── HANDOFF_PROMPT.md             ← this file
├── gslides-manifest.json         ← per-slide state, committed
├── source/
│   ├── deck.pptx                 ← gitignored — last PPTX pull
│   ├── slides/<idx>-<page>.json  ← per-slide source, committed (git-diffable)
│   └── media/                    ← gitignored — extracted images/videos
└── tools/
    ├── sync_gslides.py           ← the sync tool — read its docstring
    ├── import_pptx.py            ← one-shot PPTX → SECTIONS (use for first-pass seeding)
    └── (all other spatial-deck tools inherited)
```

---

## How to start the next session

1. Read this file top to bottom.
2. Read the upstream `tools/sync_gslides.py` docstring for the state-machine contract.
3. Run `git pull` and `python3 tools/sync_gslides.py pull --dry-run`.
4. Confirm the diff with Alex if anything is in `modified` or `removed` with `state=generated`.
5. `python3 tools/sync_gslides.py status --pending` to pick the next slide to implement.
6. Implement one slide. Mark it `generated`. Screenshot at 1920×1080 to confirm.
7. Commit. Repeat.
