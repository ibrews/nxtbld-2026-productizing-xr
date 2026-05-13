# Spatial Deck — Claude Code Instructions

## What This Is

Spatial Deck is a single-file HTML presentation framework. Everything lives in `index.html` — CSS, JS, config, content. No build process, no npm, no bundler.

## Before You Start

**Read `HANDOFF_PROMPT.md`** in the repo root. It has the full architecture guide, conventions, and common tasks. This file gives you behavioral rules; the handoff prompt gives you technical context.

## Rules

### File Structure
- **Never split `index.html` into multiple files.** The single-file design is intentional.
- **Never add npm/webpack/vite/etc.** Zero build process is a core feature.
- The only external dependency is Three.js via CDN import map (optional, for constellation map).

### Editing SECTIONS
- The `SECTIONS` array near the top of the second `<script>` block drives all slide content.
- Changing SECTIONS automatically regenerates slides on page load.
- Use `\n` for line breaks in titles. Use `<br>` and `<br><br>` in taglines.
- Use `\n` for line breaks in bullets.
- `img: 'MEDIA_CYCLER'` requires a matching IIFE after the build loop.
- `img: 'path/to/file.jpg'` renders as a standard `<img>` tag (no media cycler, no pixelated reveal). Use `MEDIA_CYCLER` with a single-item array if you want the canvas-based reveal.
- `img: 'IFRAME:url'` embeds a responsive iframe.
- `img: ''` shows a gradient placeholder.
- Build loop priority: `IFRAME:` prefix → iframe, real path → `<img>` tag, `MEDIA_CYCLER` → media cycler mount, empty → gradient placeholder.

### Media
- Store in `media/` subdirectories. Use relative paths.
- Resize images to ≤2560px: `sips --resampleWidth 2560 file.jpg`
- Videos over 100MB: `ffmpeg -i in.mp4 -vf "scale=1280:-2" -crf 28 out.mp4`
- GIFs don't animate on canvas — convert to MP4 first.
- Max 5 images per project in media cyclers (keeps file sizes reasonable).

### Git & GitHub
- **Always push immediately after every commit.** Alex and Jun work from separate Claude instances simultaneously — local-only commits cause merge conflicts.
- If a push is rejected (remote has new commits): `git pull --rebase` then `git push`.
- If the rebase has conflicts: auto-resolve when safe (non-overlapping edits, formatting-only). Flag in `REVIEW_NEEDED.md` when tricky — e.g. both sides modified the same slide in `SECTIONS`, the same IIFE, or the same CSS block. Describe what each side changed.
- Only skip the push if Alex explicitly says so.
- GitHub file size limit: 100MB. Transcode large videos before committing.
- Use `.gitignore` for files that can't go to GitHub.
- Update `HANDOFF_PROMPT.md` after significant architectural changes.

### Code Style
- The file is densely packed (long lines, minimal whitespace). Match this style.
- Use `// ── Section Name ──` comment landmarks for major blocks.
- IIFEs `(function(){...})();` for isolated features.
- `slideSteps.set()` calls must be in `setTimeout(fn, 0)` (defers past declaration).
- Find slides by: `allSlides.find(s => s.querySelector?.('.case-title')?.textContent.includes('Title'))`

### Positioning
- The annotation system exports coordinates as `left:X%, top:Y%` percentages.
- When the user says "put X here" with coordinates, use `position:absolute` with those percentages.
- Layout grid zones: A1-A4 (top row), B1-B4 (middle), C1-C4 (bottom). A1=top-left, C4=bottom-right.

### Sound
- All audio uses Web Audio API (no external files).
- `playWhoosh()` = white-noise bandpass slide transition.
- `playBing()` = soft bell for media cycler transitions.
- Wrap audio in `try{}catch(e){}` — AudioContext requires user interaction first.
- `AudioContext` is monkey-patched — all instances auto-register for cleanup.
- `window._killAllSfx()` closes all active contexts (called by `goTo()` automatically).

### URL Params & Mobile
- Default = view mode (presentation mode on, edit chrome hidden).
- `?edit` = edit mode. `?view` = explicit view. `?landscape` = orientation prompt.
- Mobile auto-detected via `(pointer:coarse)`. 👁 button toggles chrome.
- Tap = advance. Swipe = navigate. Both respect `_arrowSubstep` toggle.

### Z-Ordering
- Move mode HUD: ▲▲/▲/▼/▼▼ buttons set `style.zIndex` on last-clicked element.
- Click any element in move mode to select it for z-ordering.

### Move Mode Auto-Save
- Dragging an element in move mode auto-saves the transform as an annotation (`type: 'move'`).
- These appear in the Annotations panel immediately — no manual save step needed.
- Map node clicks are suppressed in move mode to prevent accidental navigation.

### Keyframe Animation System
- The scrubber has a `◆ KF` button that captures last-moved element's transform at current scrub time.
- Diamond markers (◆) appear on the timeline for existing keyframes; `✕ KF` deletes them.
- Keyframes are persisted as annotations (`type: 'keyframe'`).
- Two or more keyframes on the same element automatically build a WAAPI animation.
- When adding custom animations, prefer the keyframe system over manual `slideSteps` for transform-based motion.

### Settings Slide (slide 0)
- Shows "Spatial Deck Creator v0.0.5" header.
- Counter shows "00" for settings, "01" for cover.
- URL hash `#0` and `#00` both go to settings. `#N` = slide N (0-indexed).
- Arrow substep toggle: On = step through animations, Off = skip to next slide.

### Fork Defaults (apply when building any new deck from this template)
- **Agenda slide** — always include one as the first case in the first section (after the cover). Use `layout:'big'` with a `bigCaption` containing an `<ul class="agenda-list">`.
- **Company logo on cover** — always include `<div class="cover-logo-wrap"><img src="media/<slug>/logo.svg" alt="..."></div>` in the cover HTML, positioned bottom-center via the `.cover-logo-wrap` CSS class.
- **Deck QR on close slide** — once the fork is pushed to GitHub Pages (at `https://<user>.github.io/<repo>/`), add a QR card as the first item in `.close-qr-row`: `<div class="qr-card"><img src="https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=<encoded-url>" alt="QR Deck"><div class="qr-label">View the deck</div><div class="qr-badge b-amber"><user>.github.io</div></div>`. Use `b-amber` badge color to distinguish from contact QRs.
- **No lesson format for non-lesson decks** — the `slide-lesson` class and `lesson:` field in SECTIONS are for chapter-intro lesson cards (rarely appropriate for conference talks). For talks, chapter intros use `layout:'big'` cases. Only use `slide-lesson` when the deck is explicitly structured as educational lessons (e.g., a workshop with numbered lessons). The BONUS slide is the only built-in exception.

## Common Patterns

```javascript
// Add a media cycler to a case study slide
(function(){
  const slide = allSlides.find(s => s.querySelector?.('.case-title')?.textContent.includes('Project Name'));
  if (!slide) return;
  buildMediaCycler(slide, [
    {type:'image', src:'media/project/01.jpg'},
    {type:'video', src:'media/project/demo.mp4', loop:true},
  ], {imageDuration:6000});
})();

// Add multi-step animation to a slide
setTimeout(()=>{
  slideSteps.set(mySlide, {
    current: 0,
    steps: [step1Fn, step2Fn, step3Fn]
  });
}, 0);

// Position an element at a specific location
element.style.cssText = 'position:absolute;left:45%;top:30%;z-index:2';
```
