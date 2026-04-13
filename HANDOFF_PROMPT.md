# Spatial Deck — AI Agent Handoff Prompt

> **Last updated:** 2026-04-12
> **Purpose:** Read this file at the start of any AI session working on this project. It gives you everything you need to be productive immediately.
> **Maintenance:** Update this file whenever you make significant changes to the architecture, add major features, or change conventions. Future sessions depend on this being accurate.

---

## What Is This?

Spatial Deck is a single-file HTML presentation framework. Everything — CSS, JS, config, and content — lives in `index.html`. No build process, no dependencies (except Three.js via CDN for the optional constellation map).

**Repo:** https://github.com/ibrews/spatial-deck
**Live demo:** Open `index.html` in any browser
**Origin:** Built for the Harvard XR Conference 2026 keynote, then extracted and generalized. See the original keynote at https://ibrews.github.io/harvardxr-keynote/

---

## Architecture at a Glance

```
index.html
├── <style> .......................... All CSS (~200 lines, minified)
├── <script type="importmap"> ....... Three.js CDN mapping
├── <div id="deck"> ................. Slide container (empty, JS fills it)
├── <script> (first) ................ SECTIONS config + BONUS const (~50 lines)
└── <script> (second, main) ......... Everything else (~750 lines):
    ├── Settings slide creation + theme editor
    ├── Cover / Bonus / Map / Close slide creation
    ├── SECTIONS.forEach → lesson + case slide generation
    ├── buildMediaCycler() function
    ├── Auto-wrap static images
    ├── Explicit media cycler IIFEs
    ├── Map constellation builder (startMap)
    ├── Slide navigation (goTo, nextVisible, slideSteps)
    ├── Annotation system
    ├── Move mode + undo/redo
    ├── Text editing
    ├── Search overlay
    ├── Slide grid
    ├── Speaker notes + presenter popup
    ├── Duration estimator
    └── Offline export helper
```

---

## Key Conventions

### SECTIONS Array
- Each entry: `{ year, accent, lesson: {title, tagline, short, tags, notes}, cases: [{title, subtitle, img, bullets, notes}] }`
- `accent` values: `'teal'`, `'purple'`, `'amber'`, `'rose'`
- `img` values: `'MEDIA_CYCLER'` (explicit cycler IIFE needed), `'path/to/image.jpg'` (renders as `<img>` tag), `'IFRAME:url'` (embedded iframe — YouTube, pixel stream, Sketchfab, etc.), `''` (gradient placeholder)
- Build loop `img` priority: `IFRAME:` prefix → iframe, real path → `<img>` tag, `MEDIA_CYCLER` → media cycler mount, empty → gradient placeholder
- `\n` in titles renders as a line break
- `<br>` and `<br><br>` work in taglines (double = paragraph gap)
- `\n` in bullets renders as `<br>`
- `notes` field is optional; used by speaker notes system

### Slide Types & dataset Attributes
- `dataset.type`: `'settings'`, `'cover'`, `'lesson'`, `'case'`, `'bonus'`, `'map'`, `'close'`
- `dataset.year`: the section's year (string)
- `dataset.section`: index into SECTIONS array
- `dataset.hidden`: `'1'` = hidden from navigation
- `dataset.parked`: `'1'` = moved to end by PARK IIFE

### Media Cycler
- `buildMediaCycler(slideEl, items, opts)` — call after slides are built
- Items: `{type:'image'|'video', src:'path', flipH:bool, loop:bool}`
- Options: `{imageDuration, portrait, enterDur, revealDur, exitDur}`
- Canvas dynamically adapts to source aspect ratio (no cropping)
- Single-item images stop after reveal; single-item videos loop
- Find slides by: `allSlides.find(s => s.querySelector?.('.case-title')?.textContent.includes('Title'))`

### Slide Steps
- `slideSteps.set(slideEl, { current:0, steps: [fn1, fn2, ...] })`
- Each click calls the next step function before advancing to next slide
- Steps registered via `setTimeout(()=>{slideSteps.set(...)}, 0)` to defer past declaration

### Theme System
- CSS custom properties on `:root`: `--bg`, `--teal`, `--purple`, `--amber`, `--rose`, `--text`, `--dim`, `--font`, `--para-gap`, `--tagline-scale`, `--title-scale`
- Settings slide has live controls, saved to `localStorage` key `'spatial-deck-cfg'`
- Font loaded via Google Fonts `@import` that's dynamically updated

### Navigation
- `goTo(n)` — main navigation function, handles animations + per-slide-type hooks
- `nextVisible(from, dir)` — skips hidden slides
- `current` = index into `allSlides` array
- `total` = `allSlides.length`
- URL hash: `#N` jumps to slide N (0-indexed, settings=0, cover=1). `#0` and `#00` both go to settings
- Counter displays `current` (settings shows "00"); grid carousel numbering is 0-indexed (00 for settings)
- `history.replaceState` writes `#current` on every navigation

### URL Sharing Modes
- Default (no params) = view mode (presentation mode, edit chrome hidden)
- `?edit` = edit mode (all chrome visible, overrides mobile auto-hide)
- `?view` = explicit view mode
- `?landscape` = portrait-orientation prompt overlay on mobile

### Mobile
- Auto-detect via `(max-width:900px)` or `(pointer:coarse)`
- Auto-enter presentation mode; 👁 button toggles chrome
- Tap (< 15px, < 300ms) = advance step/slide
- Swipe left/right = navigate (respects steps + hidden slides)

### Arrow Substep Toggle
- `arrowSubstep` in config (default: `true`), checkbox in Settings
- When On: arrows/tap/swipe step through sub-animations before advancing
- When Off: always skip to next full slide
- `window._arrowSubstep` flag checked by all navigation handlers

### SFX Cleanup
- `AudioContext` constructor is monkey-patched to auto-register in `_activeAudioCtxs` Set
- `window._killAllSfx()` closes all active contexts — called by `goTo()` on every slide change
- No manual registration needed; all SFX functions automatically tracked

### Z-Ordering
- Move mode HUD has ▲▲/▲/▼/▼▼ buttons for Send to Front/Forward/Backward/Back
- Operates on last-clicked/dragged element via `_lastMoveEl`
- Sets `style.zIndex` on the element

### Annotations & Move Mode
- Annotations saved to `localStorage` key `'sd-annos'`
- Move transforms auto-saved as annotations (`type: 'move'`) — appear in Annotations panel immediately
- Text edits saved as: `TEXT "new content"`
- Undo/redo: 50-action stack, `Cmd+Z` / `Cmd+Shift+Z`
- **Position annotations**: clicking slide background captures `left:X%, top:Y%` coordinates
- **Layout grid**: `G` key in move mode toggles 4×3 labeled grid (A1-C4 zones)
- **Clipboard snippets**: after drag, CSS position code auto-copied to clipboard

### Keyframe Animation System
- `◆ KF` button in scrubber captures last-moved element's transform at current scrub time
- Diamond markers (◆) on timeline show existing keyframes; click to seek
- `✕ KF` deletes the keyframe at current scrub time
- Keyframes persisted as annotations (`type: 'keyframe'`)
- Two or more keyframes on the same element build a WAAPI (Web Animations API) animation automatically
- Map node clicks are suppressed in move mode to prevent accidental navigation

### Slide Transitions
- Configurable in Settings slide: `slide` (default), `fade`, `zoom`, `none`
- Saved to localStorage config as `transition` property
- `goTo()` reads preference and uses corresponding CSS keyframes

### Auto-Save Snapshots
- Every 60 seconds after first interaction, annotations + config saved to `sd-snapshots`
- Keeps last 10 snapshots; skips if nothing changed
- "🔄 Restore Snapshot" button in Settings shows timestamped list
- Restoring replaces annotations + config and reloads page

### Map Constellation
- Center text: "IS XR RIGHT / FOR YOUR PROJECT?" (updates with deck content)
- Bonus node positioned bottom-right outside the circle
- Node clicks suppressed in move mode

### Settings Slide
- Shows "Spatial Deck Creator v0.0.5 / by Alex Coulombe" header
- Slide 0, accessible via `#0` or `#00`

### Speaker Notes
- `notes` field in SECTIONS config (string)
- `N` key opens presenter popup (BroadcastChannel sync)
- `Shift+N` toggles inline drawer
- Duration estimator: ~20s/bullet, ~150wpm prose, 30s default per noteless slide

---

## Common Tasks

### Add a new lesson with cases
1. Add entry to SECTIONS array with year, accent, lesson, cases
2. If using MEDIA_CYCLER, add an IIFE after the build loop:
   ```javascript
   (function(){
     const slide = allSlides.find(s => s.querySelector?.('.case-title')?.textContent.includes('Title'));
     if (!slide) return;
     buildMediaCycler(slide, [{type:'image', src:'media/...'}], {imageDuration:6000});
   })();
   ```
3. If the lesson needs multi-step animation, register `slideSteps`

### Change the theme
- Edit CSS custom properties in `:root` for defaults
- Or use the Settings slide live controls (persisted to localStorage)

### Add media
1. Copy images/videos to `media/` subfolder
2. Resize to ≤2560px: `sips --resampleWidth 2560 file.jpg --out file.jpg`
3. Videos over 100MB: transcode with `ffmpeg -i in.mp4 -vf "scale=1280:-2" -crf 28 -preset fast out.mp4`
4. Reference via relative path in SECTIONS or media cycler IIFE

### Park/hide slides
- **Park**: Add index to `PARK` array (0-indexed, pre-park position)
- **Hide**: `Ctrl+Click` thumbnail in slide grid, or set `dataset.hidden='1'`

### Export for offline
- Use the "📦 Export for Offline" button in Settings
- Or manually download Three.js + fonts (see README)

---

## Files

| File | Purpose |
|------|---------|
| `index.html` | The entire presentation |
| `images/` | AI-generated images (4 PNGs, 2 SVGs) |
| `media/` | Images, videos, GIFs (optional) |
| `docs/` | README screenshots |
| `social.html` | 1200×630 social sharing card |
| `social.png` | Pre-rendered social image |
| `README.md` | User-facing documentation |
| `HANDOFF_PROMPT.md` | You are here |

---

## Sample Content

The default deck is "Is XR Right For Your Project?" with 3 chapters and 6 case studies. Content is generic/anonymized (no client-specific references). Cover: "Spatial Deck · Open-Source Presentation Framework" / "Is XR Right For Your Project?". Bonus: "The Best XR Project Is the One You Don't Need". Closing: "Let's Talk." / "Thinking spatially?" with single QR code to the GitHub repo. Uses 6 AI-generated images from `images/` (4 PNGs, 2 SVGs). Replace SECTIONS + BONUS to create your own talk.

---

## Known Quirks

- `file://` URLs in Chrome trigger same-origin warnings for Three.js imports — harmless, or serve via `python3 -m http.server`
- AudioContext requires user interaction before first sound plays (browser policy)
- GIFs don't animate on canvas — convert to MP4 with `ffmpeg -i file.gif -pix_fmt yuv420p -c:v libx264 out.mp4`
- Very large media (>100MB) can't push to GitHub without Git LFS — transcode first
- `slideSteps` must be registered in `setTimeout(fn, 0)` to defer past the `const slideSteps` declaration

---

*Keep this file updated. Future you (and future AI sessions) will thank present you.*
