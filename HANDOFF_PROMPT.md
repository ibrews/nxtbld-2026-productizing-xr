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
- `img` values: `'MEDIA_CYCLER'` (explicit cycler IIFE needed), `'path/to/image.jpg'` (auto-wrapped), `''` (gradient placeholder)
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
- URL hash: `#N` jumps to slide N (1-indexed)

### Annotations & Move Mode
- Annotations saved to `localStorage` key matching `'spatial-deck-annotations'` or similar
- Move transforms saved as annotations: `MOVE by Δ(±Xpx, ±Ypx)`
- Text edits saved as: `TEXT "new content"`
- Undo/redo: 50-action stack, `Cmd+Z` / `Cmd+Shift+Z`

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
| `index.html` | The entire presentation (~95KB) |
| `media/` | Images, videos, GIFs (optional) |
| `docs/` | README screenshots |
| `social.html` | 1200×630 social sharing card |
| `social.png` | Pre-rendered social image |
| `README.md` | User-facing documentation |
| `HANDOFF_PROMPT.md` | You are here |

---

## Sample Content

The default deck is "What To Look For When Hiring an XR Studio" with 5 lessons and 10 case studies. It subtly promotes Agile Lens throughout. Replace SECTIONS + BONUS to create your own talk.

---

## Known Quirks

- `file://` URLs in Chrome trigger same-origin warnings for Three.js imports — harmless, or serve via `python3 -m http.server`
- AudioContext requires user interaction before first sound plays (browser policy)
- GIFs don't animate on canvas — convert to MP4 with `ffmpeg -i file.gif -pix_fmt yuv420p -c:v libx264 out.mp4`
- Very large media (>100MB) can't push to GitHub without Git LFS — transcode first
- `slideSteps` must be registered in `setTimeout(fn, 0)` to defer past the `const slideSteps` declaration

---

*Keep this file updated. Future you (and future AI sessions) will thank present you.*
