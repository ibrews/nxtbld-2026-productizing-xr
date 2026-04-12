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
- `img: 'path/to/file.jpg'` auto-wraps in a single-item media cycler (pixelated reveal).
- `img: ''` shows a gradient placeholder.

### Media
- Store in `media/` subdirectories. Use relative paths.
- Resize images to ≤2560px: `sips --resampleWidth 2560 file.jpg`
- Videos over 100MB: `ffmpeg -i in.mp4 -vf "scale=1280:-2" -crf 28 out.mp4`
- GIFs don't animate on canvas — convert to MP4 first.
- Max 5 images per project in media cyclers (keeps file sizes reasonable).

### Git & GitHub
- Commit after every meaningful change. Push frequently.
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
