# NXT BLD 2026 — Productizing XR for Architecture · AI Agent Handoff

> **READ THIS FILE TOP TO BOTTOM BEFORE TOUCHING ANY SLIDES.**
> Last updated: 2026-05-13 · Session 3 (22-slide deck: 4 chapter intros added, annotation text-edit bug fixed, slide 3 hair + UE5 boxes redesigned, slide 10 real toolbox morph, slide 20 map nav fix, slide 21 sprites pop-in)

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

The dev server config lives at `.claude/launch.json` (name: `spatial-deck-3000`, port 3000, Python `http.server`, `autoPort:false`). Serves at <http://localhost:3000>. **Cmd+Shift+R the preview tab** — there's an aggressive HTTP cache.

If port 3000 is in use, `lsof -i :3000` then kill the existing process before calling `preview_start`. The previous-session Python server lingers.

---

## Current state (after Session 3)

22 deck slides, of ~112 source slides. Numbering shifted from Session 2 because 4 product-chapter intro slides were inserted.

| # | Slide | Source | Layout |
|---|---|---|---|
| 0 | Settings (Spatial Deck Creator v0.0.5) | — | settings |
| 1 | Cover (cycle anim + Agile Lens logo) | p13 | custom HTML |
| 2 | Agenda (8 bullets + cycling markers) | p15 | `big` |
| 3 | Alex+Jun duo intro (sprites + UE5 power-up) | p16 (+p17 folded) | `intro-hxr` |
| 4 | NXT BLD: Third in a Trilogy (large QRs right-anchored) | p18 | `trilogy` |
| 5 | The Secret Graveyard intro | p19 | `big` |
| 6 | The Toolbox Nobody Talks About (12-tile collage) | p20–p34 (excl p25, p27) | `sg-collage` |
| 7 | The filenames tell the story ("temp"/"v12_finalFINAL"/"DELETE ME"/"donotdelete" — user-edited verbatim) | p19 typography | `sg-fragments` |
| 8 | The Pattern (7-node SVG flowchart + UE5 blueprint pulse animation) | p35 | `pattern-cycle` |
| 9 | What's Worth Productizing? (3-tier hierarchy) | p36 | `big` |
| 10 | Build and organize your toolbox + Right Arrow → toolbox-morph substep (cards fly into a real toolbox SVG with 4 color-coded chips and "Same toolbox. *Different questions.*" tagline) | p37 | `toolbox-grid` |
| 11 | Floor Tour intro (NEW chapter intro) | p38 intro | `big` |
| 12 | Floor plan → arrow → VR (file content swap fixed) | p38 | `placed` |
| 13 | Floor Tour Origin (3 images; ⚠ 4th GIF dropped by PPTX export) | p39 | `placed` |
| 14 | RSC + VR comparison (hierarchy fixed: VR 3× area of RSC logo) | p40 | `placed` |
| 15 | Floor Tour Productized version | p41 | `placed` |
| 16 | Blueprint Immersive intro (NEW) — accent `teal` | p44 | `big` |
| 17 | Hyperreal Estate intro (NEW) — accent `rose` | p67 | `big` |
| 18 | Holodeck Anywhere intro (NEW) — accent `purple` | p88 | `big` |
| 19 | Bonus (upstream lesson) | — | spatial-deck base |
| 20 | Map / The Journey (7 chapter nodes + BONUS, click-nav fixed) | — | spatial-deck base |
| 21 | Close (contact + QRs + **pop-in Alex+Jun sprites**) | p115 | custom HTML |

---

## Drive video URLs (Drive metadata is stripped by PPTX export — captured manually)

These slides reference videos hosted on Google Drive. The PPTX dropped the video binaries; some URLs were captured in slide text/notes by Alex so we could recover them:

| Source page | Context | Drive URL |
|---|---|---|
| p26 | Secret Graveyard | `drive.google.com/file/d/1o7qIJzwDX25qRWAi60ofs2Fdc8IXNsZ_` |
| p44 | Blueprint Immersive — "Which layouts do we actually like?" | `drive.google.com/file/d/1uhRl0E5OVqpB7_nYMHjQXoKXqW7-7VA1` |
| p61 | "Import Datasmith" | `drive.google.com/file/d/1DcUnMRNP1Ug8q_zIXIV89XBg99THZq7o` |
| p63 | "Jump to seat" | `drive.google.com/file/d/19XlCnYgDuLcsO0K67J6Vye0dqX7-xP2V` |
| p64 | "Design options" (same as p44) | `drive.google.com/file/d/1uhRl0E5OVqpB7_nYMHjQXoKXqW7-7VA1` |
| p74 | *(untitled)* | `drive.google.com/file/d/1RAdPw-eigVu5-16mWSJEG7a7tX7I3A1-` |
| p76 | *(untitled)* | `drive.google.com/file/d/1exxhg7yv2lkpxoGq-9DT297JstNNW8wQ` |
| p84 | "Gifs at various resolutions" — Drive **folder** | `drive.google.com/drive/folders/1DyUxmxK2f9o9hMFO4QquVCFk7i8QhKbU` |
| p99 | *(untitled)* | `drive.google.com/file/d/1SXAUxtVYJlNcSHke3oN7EHQodWTBYZo3` |
| p100 | *(untitled)* | `drive.google.com/file/d/1edKWxk0zROShb-hXweH5MeIx9SPtBwRl` |
| p105 | *(in speaker_notes only)* | `drive.google.com/file/d/1wHbNiKbU0T5PBD9zcGbRn0J5RYdLG5hA` |

p74, p76, p99, p100, p105 are completely untitled — Alex needs to identify which product chapter each one belongs to before building.

---

## Top priority for the NEXT session

**1. Build the unbuilt product-chapter content.** ~80 source slides waiting. After each chapter's intro slide (already built):
- Blueprint Immersive content (p44–p66, ~22 slides)
- Hyperreal Estate content (p67–p86, ~12 slides — p86 now NOT skipped, see "Skip slide drift" below)
- Holodeck Anywhere content (p88–p108, ~20 slides)
- The Pipeline (p109–p110)
- AI chapter (p111–p112) — ⚠ p111 has draft text "No idea if this is true…" that violates VERBATIM
- "Where Are You in the Cycle?" callback (p113)
- "Secret 5th Rung" (p114)

**2. Slide 13 missing 4th image.** Source p39 has a 4th `<p:pic>` (`Villa Floorplan Walkthrough F.gif`) at top-right, but the PPTX export stripped its binary (picture frame exists, `r:embed` missing). Either (a) re-export `source/deck.pptx` from Google Slides — may be transient, or (b) Alex manually downloads the GIF and drops it at `media/nxtbld/floor-27-d.{png|gif}`, then wire into placedItems at ~x:55, y:2, w:42, h:24.

**3. Speaker notes additions never surfaced.** Audit found scripted opening lines for slides 9 (J), 11 (J), 12 (A), 13 (A) that aren't in the deck's speaker-notes display. Surface them.

**4. p17 client logo wall.** Currently folded into slide 3. Source still asks for it. Decide: separate slide or keep folded.

**5. p36 "drop in keywords" NOTE directive.** Add `colocation` / `Data ingestion` / `multiuser` / `Optimization pipeline` visual to slide 9.

---

## Critical conventions

### Speaker note markers
`A:` = Alex speaks · `J:` = Yu-Jun speaks · `A J` = both. Preserve verbatim from source.

### VERBATIM rule
Source slide body text NOT prefixed with `NOTE:` must appear on the deck slide as-is. **Do not invent or paraphrase.** If you have a real alternative, build an ADDITIONAL slide with `alt:'<reason>'` flag right after — it renders with an `[ALT]` corner badge.

**Exception (slide 7):** Alex explicitly overrode source fragments via annotation tool. Current fragments are `"temp"` / `"v12_finalFINAL"` / `"DELETE ME"` / `"donotdelete"` — these are user direction, NOT source. Don't revert.

### NOTE: directives
Source body text prefixed with `NOTE:` is an instruction TO YOU describing something to generate (animation, diagram, sprite scene, layout). The text after `NOTE:` is the spec, NOT slide copy.

### Google Slides "Skip slide" → never use content from these
The Google Slides "Skip slide" feature marks slides as `<p:sld show="0">` in the PPTX. **Never put their text or media in the deck.** To find them:

```bash
unzip -q -o source/deck.pptx 'ppt/slides/*.xml' -d /tmp/check
for f in /tmp/check/ppt/slides/slide*.xml; do
  grep -l 'show="0"' "$f" > /dev/null && \
    echo "$(basename $f .xml | sed 's/slide//') skipped"
done | sort -n
```

**Skip slide drift between syncs:** as of 2026-05-13 sync, skipped slides are 2, 13, 15, 45, 46, 47, 48, **73**. Previously slide 74 was skipped instead of 73. Means p85 "COMPARISON MODELS" is now hidden but p86 "Hyperreal Estate" is now live. Re-run the check every sync — Alex toggles skip flags.

### Media filename stability across syncs
**The PPTX export renumbers `image*.png` between pulls.** What was `image10.png` in one pull is a totally different image in the next. **Never reference `source/media/imageN.*` directly from `index.html`.** Always copy to `media/nxtbld/<semantic-name>.png` first.

**Worse: file *contents* can also shift even when names match.** During Session 3 we discovered `media/nxtbld/floor-26-plan.jpg` actually contained the VR shot and `floor-26-vr.png` contained the floor plan — the filenames had become wrong after a prior sync. Fix was to swap `src:` paths in the placedItems rather than rename files. Always sanity-check images by content when slides look wrong.

Current scheme:
- `jun.png` — Yu-Jun's headshot (slide 4 first media, unused after trilogy rebuild)
- `trilogy-talk1.png` (NXT BLD II) / `trilogy-talk2.png` (NXT BLD I) — talk thumbnails
- `sg-01.png`…`sg-16.png` — Secret Graveyard collage tiles, slotted by non-skipped slide order
- `toolbox-1.png`, `toolbox-2.png`, `toolbox-3.mp4`, `toolbox-4.jpg` — slide 10 products
- `floor-26-plan.jpg` (actually VR shot), `floor-26-vr.png` (actually plan), `floor-27-{a,b,c}.{png,mp4}`, `floor-28-{a,b}.png`, `floor-29-{a,b}.png`
- `agilelens_logo.svg` — cover logo (white-on-dark via `filter:brightness(0) invert(1)`)
- `GoldAuthorized.png` + `ue5logo.png` at REPO ROOT — UE5 fireball projectiles

---

## DO NOT

1. Generate slide body text that isn't called for by a `NOTE:` directive. Verbatim from source. (Slide 7 is a documented user-override exception.)
2. Use any content from slides marked `show="0"` (Google Slides "Skip slide").
3. Reference `source/media/imageN.*` directly from `index.html` — image numbers shift between syncs.
4. Add per-chapter lesson slides. The build loop intentionally skips them. Chapter intros are regular `layout:'big'` cases (e.g., slides 11, 16, 17, 18).
5. Manually edit `source/slides/*.json` or `gslides-manifest.json` — both are generated. Edit Google Slides and `pull`.
6. **Set `transform-origin: center bottom` on the avatar inner anim** — it resolves to the SVG viewport center, not the avatar's, and causes walkers to float ~200px above the floor. Leave at default (0,0). (See "Lessons learned" below.)
7. Commit files >10MB without checking `.gitignore`. `source/deck.pptx` is gitignored.
8. Trust the preview SUBAGENT's filesystem grep — they inherit the *session's* cwd. Use the `mcp__Claude_Preview__*` tools DIRECTLY for verification.
9. **Fan out parallel background agents on the same dense single-file repo without thinking about it.** Three concurrent agents writing `index.html` is technically OK because Edit uses exact-string matching, but a 4th agent dispatch when context is large will burn the 500-tool-call limit. Prefer 2 agents max in flight unless tasks touch fully disjoint file regions.

## DO

1. **Re-sync at the start of every session.** `pull --dry-run` then `pull`. Audit text + media changes for ALREADY-BUILT slides before adding new ones.
2. **Cmd+Shift+R** the preview tab before judging anything visual.
3. **Use the preview MCP tools directly** — `preview_start`, `preview_eval`, `preview_screenshot`, `preview_snapshot`, `preview_resize`. The preview subagents bounce off cwd confusion.
4. **Resize preview to 1920×1080** before judging sprite slides — the `.intro-grid` switches to column layout below 900px.
5. **Press Right Arrow on slide 3** to advance through substeps. Substep flow has changed — see "Duo intro substeps" below.
6. **Mark slides `generated` as you implement them** — `python3 tools/sync_gslides.py mark <page-id> generated --deck-target "SECTIONS[N].cases[M]"`.
7. **Spawn background agents for substantive work** with `run_in_background:true` so the user can keep typing notes. End your turn quickly after spawning. Don't verify in the same turn as the spawn.

---

## Custom layouts in this fork

| Layout | Where | Purpose |
|---|---|---|
| `intro-hxr` | slide 3 | Two pixel-art walker sprites walk in, jump, grab VR headsets, power up — then UE5 substep: re-jump to TWO UE5 boxes (at headset positions x=140, x=260) and fireball storm |
| `trilogy` | slide 4 | 2-up: thumbnail + year/title + LARGE QR (max 140px, right-anchored via `flex-direction:row-reverse`) |
| `sg-collage` | slide 6 | 12-tile collage with sticky-note text overlays |
| `sg-fragments` | slide 7 | 4 stylized filenames in 2×2 grid (distinct colors) + punchline |
| `pattern-cycle` | slide 8 | 7-node SVG flowchart with UE5-blueprint-style pulse + flow animations |
| `toolbox-grid` | slide 10 | 4 product cards (`aspect-ratio:4/3` images) with Right Arrow → toolbox-morph substep |
| `big` | slides 2, 5, 9, 11, 16, 17, 18 | Statement slides. Accent classes: `amber` / `teal` / `rose` / `purple` |
| `placed` (extended) | slides 12–15 | `placedItems:[{type,src,x,y,w,h,...}]` with `img`/`mp4`/`arrow`/`qr-card` types |
| close + sprites | slide 21 | Contact pills + QRs + pop-in Alex/Jun avatars (left/right) |

**Animation helpers** (in IIFEs near the bottom of the main script):
- `buildAvatar(parent, opts)` — pixel-art SVG, supports `withBeard`/`withGlasses`/`longHair`/`noBrows` flags
- `paintLongHair(body, opts)` — **asymmetric center-parted style** (Jun): more swoop on left, less on right, scalp visible at x=-2..2
- `paintWornHeadset(body)` — VR visor painted after power-up
- `makeUE5Box(x, y)` + `playUE5CollectSfx()` — glowing crate at headset positions for the UE5 substep
- `shootFireball(svg, x, y, dir)` — random UE5/GoldAuthorized projectile
- Web Audio: `playIntroPowerUpSfx`, `playZapSfx`, `playTallyTick`, `playTallyChing`, `playBing`, `playToolboxThud`

---

## Duo intro substeps (slide 3) — updated timing

1. **Auto on slide entry** (MutationObserver on `.active`): walkers walk in from offstage, jump to two VR headset boxes at x=140 (Alex) and x=260 (Jun), grab them, flash + sparkle, power up, fall back at scale 1.4 with worn VR headsets.
2. **Right Arrow** → `showBio`: eyebrow ("WHO WE ARE?") / title ("Agile Lens") / sub ("Architects turned XR-chitects…") / sub-UE5 / names fade in.
3. **Right Arrow again** → `playDuoUE5PowerUp`: **TWO UE5 boxes** fade in at the same x positions as the headsets used to occupy (140, 260, y=200). Walkers re-jump (1400ms), boxes explode (2200ms), flash + power-up (2440ms), fall (4040ms), then ~4s fireball storm (5240ms+). Timings doubled from Session 2 so "UE5" reads clearly before explode.
4. **Right Arrow once more** → `showStats`: 4 stat tiles tally from 0 (16/10/8/100+) with tick-per-number + closing chime.

**Substep reset on slide return.** `goTo()` now calls `entry.reset && entry.reset(); entry.current = 0` when entering a slide that has registered `slideSteps`. Slide 10 has an explicit `resetToolboxMorph`. Slide 3 resets via the existing MutationObserver path. Re-entering a slide replays its animation.

---

## Close slide (slide 21) sprite pop-in

- Two `<svg class="close-sprite close-sprite-alex/-jun">` containers added to the close-slide HTML, positioned `position:absolute; bottom:clamp(80px,12vh,170px)` with `left`/`right` anchors.
- IIFE paints them via `buildAvatar` (Alex: `withBeard:true`; Jun: matching slide 3 config), then `paintLongHair` for Jun.
- MutationObserver on `.active`: on entry, Alex pops at 200ms, Jun at 500ms with `playBing()` chime. On leave, removes `.popped` class so re-entry replays.
- The `.popped` keyframe is elastic: opacity 0→1, scale 0.3→1.1→1, translateY −20px→0 over 600ms.

---

## Annotation system

**Text-edit persistence was fixed in Session 3** (commit `114f9a3`). `endEdit()` now captures `newText` vs `origText`, builds a `type:'text-edit'` entry with `selector` + `context` + `position`, upserts into the annotations array, and persists via `aS()` + `aRender()`. Previously it only fired a toast.

Move/transform annotations capture position changes via the move-mode handler. They were already working. They export as transforms like:
```
TRANSFORM scale 0.92 → 1.05 — position: left:0.4%, top:19.9%
TRANSFORM translate Δ(+48px, +6px) → final position: left:2.2%, top:21.3%
```

To bake an annotation into source: extract the final `left:X%, top:Y%` for `x` and `y`, multiply `w`/`h` by the scale factor.

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
├── .claude/
│   ├── CLAUDE.md
│   └── launch.json               ← preview-server config (python3 http.server 3000)
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

- [ ] **Build chapter content for Blueprint Immersive, Hyperreal Estate, Holodeck Anywhere, Pipeline, AI, Where Are You, Secret 5th Rung.** ~80 source slides waiting.
- [ ] **Slide 13 missing 4th image** — PPTX export stripped binary for `Villa Floorplan Walkthrough F.gif`. Re-export deck.pptx OR manually download and drop at `media/nxtbld/floor-27-d.{png|gif}`.
- [ ] **Speaker notes — surface scripted opening lines** for slides 9, 11, 12, 13 in the deck's notes display.
- [ ] **p17 client logo wall** — currently folded into slide 3. Source asks for it. Decide: separate slide or keep folded.
- [ ] **p36 keywords directive** — add `colocation` / `Data ingestion` / `multiuser` / `Optimization pipeline` visual to slide 9.
- [ ] **p111 draft text** — "No idea if this is true, but…" violates VERBATIM. Get clarification from Alex before building.
- [ ] **`notes-config.json` 404 spam** in browser network panel. Benign — speaker-notes sync polling. Ship a stub or guard the fetch.
- [ ] **Cycle icons on cover** — may want different icons as the cycle metaphor evolves.

---

## Lessons learned (worth keeping)

1. **`transform-origin: center bottom` on an SVG `<g>` resolves to the SVG VIEWPORT's center-bottom, not the element's BBox center-bottom.** This caused walkers to float ~200px above the floor for an entire session.
2. **PPTX `image*.png` filenames are not stable across exports — AND file contents can become misaligned with semantic-named copies.** Always copy to `media/nxtbld/<semantic-name>` first AND sanity-check by visual content when slides look wrong.
3. **Google Slides "Skip slide" → PPTX `<p:sld show="0">`.** Detect and exclude.
4. **Google Slides → PPTX export drops Drive video binaries AND occasionally Drive image binaries.** Picture frames remain with no `r:embed`. Re-export sometimes fixes it.
5. **The preview subagent inherits the session's cwd.** Use `mcp__Claude_Preview__*` tools directly.
6. **`mix-blend-mode: color-dodge` over animated blurred blobs flickers because overlap saturates → color-dodge denominator → 0 → spike white.** Fix: `isolation:isolate` on the `.bg` container + reduce blob opacity (b1 0.45→0.32, b2 0.42→0.30, b3 0.28→0.22).
7. **The pixel-art brow draws were duplicated — once unconditionally in the hair block, once inside `if(!opts.noBrows)`.** Removing the conditional alone didn't remove Jun's brows. Always check for shadow duplicates when a "skip" flag isn't working.
8. **Annotations don't persist text edits unless `endEdit()` writes to the annotations array.** Toast alone is not persistence. Look for the upsert logic, not just the UI feedback.
9. **Background agents on a single dense file work fine in parallel if their regions don't overlap, but watch the 500-tool-call session limit.** Each agent burns ~20–60 tool calls. Three concurrent agents + main-thread verification + new note dispatch eats the budget fast.
10. **Don't verify in the same turn as you spawn an agent** — your turn stays "running" and blocks the user from typing the next note.
11. **The map slide's `lessonIdxs` array was declared but never populated** after a refactor removed lesson slides. Click handlers silently no-op'd. When a feature "should just work" and doesn't, grep for the variable feeding the conditional — it may be a vestigial empty array.
