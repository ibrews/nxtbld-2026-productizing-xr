# NXT BLD 2026 — Productizing XR for Architecture · AI Agent Handoff

> **READ THIS FILE TOP TO BOTTOM BEFORE TOUCHING ANY SLIDES.**
> Last updated: 2026-05-13 · Session 2 (~15 deck slides built, slide 3 sprite fixed, SG intro restored, skip-slides honored)

---

## What this repo is

A [Spatial Deck](https://github.com/ibrews/spatial-deck) fork for **Alex Coulombe** + **Yu-Jun Yeh** at NXT BLD 2026 on **May 14, 2026** — talk title: *"Productizing XR for Architecture — Where Are You in the Cycle?"*

**Source of truth:** Google Slides — <https://docs.google.com/presentation/d/1cbYlmcqXFU-lgHIM-259cZyx2ircKLoz6vUopCKsxvA/edit>

**Companion decks (read their HANDOFFs):**
- [ibrews/fmx-2026-spatial-storytelling](https://github.com/ibrews/fmx-2026-spatial-storytelling) — origin of the sprite layout we ported
- [ibrews/harvardxr-keynote](https://github.com/ibrews/harvardxr-keynote) — origin of `intro-hxr` walker animation

---

## How to start the next session (DO THIS FIRST)

```bash
cd /Users/alex/git/nxtbld-2026-productizing-xr
git pull
python3 tools/sync_gslides.py pull --dry-run    # see what changed
python3 tools/sync_gslides.py pull              # apply
python3 tools/sync_gslides.py status --pending  # what's left
```

The dev server is already configured in `.claude/launch.json` upstream (name: `spatial-deck-3000`). It serves this repo at <http://localhost:3000>. **Cmd+Shift+R the preview tab** — there's an aggressive HTTP cache.

---

## Current state (after Session 2)

15 deck slides + cover + close, of ~111 source slides:

| # | Slide | Source | Layout |
|---|---|---|---|
| 1 | Cover (cycle anim + Agile Lens logo) | p13 | custom HTML |
| 2 | Agenda (8 bullets + cycling markers) | p15 | `big` |
| 3 | Alex+Jun duo intro (pixel sprites + UE5 power-up) | p16 (+p17 folded) | `intro-hxr` |
| 4 | Third in a Trilogy (2 QR cards + thumbnails) | p18 | `trilogy` |
| 5 | The Secret Graveyard intro | p19 | `big` |
| 6 | The Toolbox Nobody Talks About (12-tile collage, skips honored) | p20–p34 (excl p25, p27) | `sg-collage` |
| 7 | The filenames tell the story | p19 typography | `sg-fragments` |
| 8 | The Pattern (7-node SVG flowchart) | p35 | `pattern-cycle` |
| 9 | What's Worth Productizing? | p36 | `big` |
| 10 | Build and organize your toolbox (4 cards) | p37 | `toolbox-grid` |
| 11–14 | Floor Tour series | p38–p41 | `placed` |
| 15 | Bonus (upstream) | — | spatial-deck base |
| 16 | Map (upstream) | — | spatial-deck base |
| 17 | Close (contact pills + 2 LinkedIn QRs) | was p109, now p102 in latest sync | custom HTML |

---

## Top priority for the NEXT session

**1. Ingest the latest Google Slides updates — especially the videos.** Alex has been adding videos. The user said:

> "looking at all the updates to google slides (especially all the videos I've added, noted by google drive links since that metadata seems to get lost when a google slides deck gets downloaded)"

So when you `pull`:
- `sync_gslides.py` will catch new slides + text + image changes
- **But Google Drive video embeds get LOST in the PPTX export** — they appear as black-box placeholders in the source. To recover the real Drive URLs, **manually open the live Google Slides** and check each modified/new slide for embedded videos. Cross-reference with the slide's notes for any drive.google.com link the user typed.
- Update `source/slides/<page-id>.json` manually with the Drive URLs if helpful, or just note them in your session context.

**2. Fresh QA notes pass.** Alex will share new feedback after looking at the current rebuilt deck. Expect notes on slides 3 (duo intro), 5–7 (Secret Graveyard sequence), 8 (The Pattern), 11–14 (Floor Tour), 17 (close).

**3. Slides 30–101 not built yet.** ~80 source slides waiting. The product chapters (Blueprint Immersive, Hyperreal Estate, Holodeck Anywhere), the callback "Where Are You in the Cycle?" (source p107), the "Secret 5th Rung" (source p108), plus the close at the new p102.

**4. Close slide page-id mismatch.** Currently `index.html` line ~1136 has `cls.dataset.deckTarget='p109'` but the latest sync moved it to p102. Update.

---

## Critical conventions

### Speaker note markers
`A:` = Alex speaks · `J:` = Yu-Jun speaks · `A J` = both. Preserve verbatim from source.

### VERBATIM rule
Source slide body text NOT prefixed with `NOTE:` must appear on the deck slide as-is. **Do not invent or paraphrase.** If you have a real alternative, build an ADDITIONAL slide with `alt:'<reason>'` flag right after — it renders with an `[ALT]` corner badge.

### NOTE: directives
Source body text prefixed with `NOTE:` is an instruction TO YOU describing something to generate (animation, diagram, sprite scene, layout). The text after `NOTE:` is the spec for that generation, NOT slide copy.

### Google Slides "Skip slide" → never use content from these
The Google Slides "Skip slide" feature marks slides as `<p:sld show="0">` in the PPTX. **Never put their text or media in the deck.** To find them:

```bash
unzip -q -o source/deck.pptx 'ppt/slides/*.xml' -d /tmp/check
for f in /tmp/check/ppt/slides/slide*.xml; do
  grep -l 'show="0"' "$f" > /dev/null && \
    echo "$(basename $f .xml | sed 's/slide//') skipped"
done | sort -n
```

As of 2026-05-13: source slides 2, 13, 15, 45, 46, 47, 48, 74 are skipped. **The SG collage on deck slide 6 already excludes p25 + p27** (source slides 13 + 15).

### Media filename stability across syncs
**The PPTX export renumbers `image*.png` between pulls.** What was `image10.png` in one pull is a totally different image in the next. **Never reference `source/media/imageN.*` directly from `index.html`.** Always copy to `media/nxtbld/<semantic-name>.png` first. Current scheme:

- `jun.png` — Yu-Jun's headshot (slide 4 first media)
- `trilogy-talk1.png` (NXT BLD II, Architect in Metaverse) / `trilogy-talk2.png` (NXT BLD I, How VR Helped Theater) — talk thumbnails
- `sg-01.png` … `sg-16.png` — Secret Graveyard collage tiles, slotted by non-skipped slide order (gaps where slides 13 + 15 are skipped)
- `toolbox-1.png`, `toolbox-2.png`, `toolbox-3.mp4`, `toolbox-4.jpg` — slide 25 (4 products)
- `floor-26-plan.jpg`, `floor-26-vr.png`, `floor-27-{a,b,c}.{png,mp4}`, `floor-28-{a,b}.png`, `floor-29-{a,b}.png` — Floor Tour series
- `agilelens_logo.svg` — cover logo (white-on-dark via `filter:brightness(0) invert(1)`)
- `GoldAuthorized.png` + `ue5logo.png` at REPO ROOT — UE5 fireball projectiles for slide 3's UE5 power-up substep

---

## DO NOT

1. Generate slide body text that isn't called for by a `NOTE:` directive. Verbatim from source.
2. Use any content from slides marked `show="0"` (Google Slides "Skip slide").
3. Reference `source/media/imageN.*` directly from `index.html` — image numbers shift between syncs.
4. Add per-chapter lesson slides. The build loop intentionally skips them. Chapter intros are regular `layout:'big'` cases.
5. Manually edit `source/slides/*.json` or `gslides-manifest.json` — both are generated. Edit Google Slides and `pull`.
6. **Set `transform-origin: center bottom` on the avatar inner anim** — it resolves to the SVG viewport center, not the avatar's, and causes walkers to float ~200px above the floor. Leave at default (0,0). (See "Lessons learned" below — this was an entire session's hunt to find.)
7. Commit files >10MB without checking `.gitignore`. Source/deck.pptx is gitignored.
8. Trust the preview SUBAGENT's filesystem grep — they inherit the *session's* cwd which is `/Users/alex/git/fmx-2026-spatial-storytelling/`, not this repo. They will report wrong things. Use the `mcp__Claude_Preview__*` tools DIRECTLY for verification.

## DO

1. **Re-sync at the start of every session.** `pull --dry-run` then `pull`.
2. **Cmd+Shift+R** the preview tab before judging anything visual.
3. **Use the preview MCP tools directly** — `preview_start`, `preview_eval`, `preview_screenshot`, `preview_snapshot`, `preview_resize`. The preview subagents bounce off cwd confusion.
4. **Resize preview to 1920×1080** before judging sprite slides — the `.intro-grid` switches to column layout below 900px.
5. **Press Right Arrow on slide 3** to advance through substeps: `showBio` → `playDuoUE5PowerUp` (fireball storm + subUE5 reveal) → `showStats` (count-up tally with chime).
6. **Mark slides `generated` as you implement them** — `python3 tools/sync_gslides.py mark <page-id> generated --deck-target "SECTIONS[N].cases[M]"`.

---

## Custom layouts in this fork

| Layout | Where | Purpose |
|---|---|---|
| `intro-hxr` | slide 3 | Two pixel-art walker sprites (Alex + Yu-Jun) walk in, jump, grab VR headsets, power up, then UE5 power-up substep with fireballs |
| `trilogy` | slide 4 | 2-up: thumbnail + year/title + QR per talk |
| `sg-collage` | slide 6 | 12-tile collage with sticky-note text overlays |
| `sg-fragments` | slide 7 | 4 stylized filenames in 2×2 grid (distinct colors) + punchline |
| `pattern-cycle` | slide 8 | 7-node SVG flowchart of the productize-vs-rebuild cycle |
| `toolbox-grid` | slide 10 | 4 product cards with name + question tagline |
| `placed` (extended) | slides 11–14 | Now accepts `placedItems:[{type,src,x,y,w,h,...}]` with `img`/`mp4`/`arrow`/`qr-card` types in addition to legacy `placedImages` arrays |

Animation helpers (in the duo intro IIFE near the bottom of `index.html`'s main script): `buildAvatar` (pixel-art SVG, supports `withBeard`/`withGlasses`/`longHair`/`noBrows` flags), `paintLongHair` (Jun's curtains), `paintWornHeadset` (the VR visor painted on after power-up), `shootFireball` (UE5/GoldAuthorized projectiles), `playIntroPowerUpSfx`/`playZapSfx`/`playTallyChing` (Web Audio synth).

---

## Duo intro substeps (slide 3)

1. **Auto on slide entry** (MutationObserver on `.active` class): walkers walk in from offstage, jump, grab headsets, flash + sparkle, power up, fall back at scale 1.4 with worn VR headsets.
2. **Right Arrow** → `showBio`: eyebrow/title ("Agile Lens")/sub/names fade in.
3. **Right Arrow again** → `playDuoUE5PowerUp`: re-jump + flash + power up + ~4s of hop-around-firing UE5 fireballs while the UE5 sub-text fades in.
4. **Right Arrow once more** → `showStats`: 4 stat tiles tally from 0 (16/10/8/100+) with tick-per-number + closing chime.

---

## Files at a glance

```
nxtbld-2026-productizing-xr/
├── index.html                    ← The deck. All CSS + JS + SECTIONS in one file.
├── README.md
├── HANDOFF_PROMPT.md             ← this file
├── gslides-manifest.json         ← per-slide state, committed
├── GoldAuthorized.png            ← UE5 fireball asset (root, referenced by JS)
├── ue5logo.png                   ← UE5 fireball asset (root, referenced by JS)
├── source/
│   ├── deck.pptx                 ← gitignored — last PPTX pull (~236 MB)
│   ├── slides/<idx>-<page>.json  ← per-slide source, committed (git-diffable)
│   └── media/                    ← gitignored — all extracted images/videos
├── media/
│   ├── nxtbld/                   ← stable semantic-named media (committed)
│   └── …                         ← upstream spatial-deck samples
└── tools/
    ├── sync_gslides.py           ← the sync tool — read its docstring
    └── …                         ← all other spatial-deck tools inherited
```

---

## Known issues / TODOs

- [ ] **Google Drive video links lost in PPTX export.** Manually cross-reference live Google Slides URLs for each video. `sync_gslides.py` can't capture these because Google encodes them as OLE placeholders.
- [ ] **Close slide page-id mismatch.** Hardcoded `'p109'` in `index.html` (close slide); latest sync moved Ending/Thank you to `p102`. Update.
- [ ] **`notes-config.json` 404 spam** in browser network panel. Benign — speaker-notes sync polling. Ship a stub or guard the fetch.
- [ ] **Slide 25 "Build your toolbox" morph animation.** Source NOTE asks for the 4 product images to morph into a labeled toolbox as a second step. Currently static 4-card grid. Add as a `slideSteps` step.
- [ ] **Slides 30–101 not built.** Blueprint Immersive, Hyperreal Estate, Holodeck Anywhere, "Where Are You in the Cycle?" callback (p107), "Secret 5th Rung" (p108), close (p102). ~80 source slides.
- [ ] **Cycle icons on cover** — currently spreadsheet, blueprint, VR headset, render-triangle, laptop, city-skyline. May want different icons as the cycle metaphor evolves.

---

## Lessons learned this session (worth keeping)

1. **`transform-origin: center bottom` on an SVG `<g>` resolves to the SVG VIEWPORT's center-bottom, not the element's BBox center-bottom.** This caused walkers to float ~200px above the floor for an entire session. Fix: leave inner anim's transform-origin at default (0,0) and let scale grow the avatar downward from its head-top.
2. **PPTX `image*.png` filenames are not stable across exports.** Always copy to `media/nxtbld/<semantic-name>` first. Bit me twice.
3. **Google Slides "Skip slide" → PPTX `<p:sld show="0">`.** Detect and exclude when picking source content.
4. **The preview subagent inherits the session's cwd.** When my cwd is `/Users/alex/git/fmx-2026-spatial-storytelling/` and the agent does a filesystem grep, it sees FMX content and reports wrong things. Use `mcp__Claude_Preview__*` tools directly when verifying.
5. **A 9px `--floor` clip looks "stood on the floor" visually.** Don't overthink walker-floor positioning math; it just needs to look like the feet are at the line.
