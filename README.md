# 🎭 Spatial Deck

**The presentation framework for people who think spatially.**

A single-file HTML presentation system built for XR professionals, creative technologists, and anyone who wants more control over their slides than PowerPoint will ever give you. Zero dependencies. Zero build process. One file to rule them all.

> *Designed at [Agile Lens](https://agilelens.com) — a 10-year-old immersive design studio that has given talks at Harvard, SIGGRAPH, the Kennedy Center, and everywhere in between.*

---

## ✨ What Makes This Different

| Feature | PowerPoint | Google Slides | Spatial Deck |
|---------|-----------|--------------|-------------|
| Single file, no cloud | ❌ | ❌ | ✅ |
| Live annotation mode | ❌ | ❌ | ✅ |
| Drag-to-reposition anything | ❌ | ✅ | ✅ |
| Undo/redo in layout mode | ✅ | ✅ | ✅ |
| Media cycler with pixelated reveal | ❌ | ❌ | ✅ |
| Animated constellation map | ❌ | ❌ | ✅ |
| Web Audio sound effects | ❌ | ❌ | ✅ |
| Full theme editor (live) | Limited | Limited | ✅ |
| Speaker notes + timing estimator | ✅ | ✅ | ✅ |
| Multi-step slide animations | Limited | Limited | ✅ |
| Works offline from a USB stick | ❌ | ❌ | ✅ |
| AI-friendly (LLM can edit it) | ❌ | ❌ | ✅ |
| Version control with Git | ❌ | ❌ | ✅ |
| Runs on any device with a browser | ❌ | ✅ | ✅ |

---

## 🚀 Quick Start

```bash
# Clone it
git clone https://github.com/ibrews/spatial-deck.git
cd spatial-deck

# Open it
open index.html
# That's it. No npm install. No webpack. No tears.
```

---

## 🎯 How It Works

### The SECTIONS Array

Everything in your presentation is driven by a single JavaScript array at the top of `index.html`:

```javascript
const SECTIONS = [
  {
    year: 2024, accent: 'teal',
    lesson: {
      title: 'Your Lesson Title\nWith Line Breaks',
      tagline: 'The body text that explains the lesson...',
      short: 'SHORT TAG',
      tags: 'Tag One · Tag Two · Tag Three',
      notes: 'Speaker notes: what to say when this slide is up'
    },
    cases: [
      {
        title: 'Case Study Title',
        subtitle: 'One-line description',
        img: 'MEDIA_CYCLER',  // or 'path/to/image.jpg' or ''
        bullets: ['Point one', 'Point two', 'Point three'],
        notes: 'Talking points for this case study'
      },
    ]
  },
  // ... more sections
];
```

Change the data → the slides update. That's the whole mental model.

### Slide Types

| Type | Created From | Purpose |
|------|-------------|---------|
| `cover` | Hardcoded | Title slide |
| `lesson` | `SECTIONS[].lesson` | Year + lesson title + tagline |
| `case` | `SECTIONS[].cases[]` | Image/media + title + bullets |
| `bonus` | `BONUS` const | Special amber-accent closer |
| `map` | Auto-generated | Animated constellation of all lessons |
| `close` | Hardcoded | QR codes + contact info |
| `settings` | Auto-generated | Hidden slide 0 with live controls |

---

## 🎮 Keyboard Shortcuts

### Presentation Mode
| Key | Action |
|-----|--------|
| `→` `Space` `PageDown` | Next slide |
| `←` `PageUp` | Previous slide |
| `Home` | First slide |
| `End` | Last slide |
| `H` | Toggle UI chrome (presentation mode) |
| `G` | Jump to slide by number |
| `Cmd/Ctrl + F` or `/` | Search all slide text |
| `N` | Open presenter popup (speaker notes) |
| `Shift + N` | Toggle inline notes drawer |

### Move Mode (`M` to toggle)
| Key/Action | Effect |
|------------|--------|
| `Drag` | Translate element |
| `Shift + Drag` | Scale element |
| `Alt/Option + Drag` | Rotate element |
| `Cmd/Ctrl + Click` | Select parent element |
| `Cmd/Ctrl + Z` | Undo |
| `Cmd/Ctrl + Shift + Z` | Redo |
| `Double-click` | Edit text inline |

### Text Editing (double-click in Move Mode)
| Key | Effect |
|-----|--------|
| `Enter` | New bullet (when editing a `<li>`) |
| `Shift + Enter` | Line break within element |
| `Backspace` on empty bullet | Delete bullet |
| `Cmd/Ctrl + Enter` | Save and exit edit mode |
| `Escape` | Cancel edit |

### Annotation Mode (`A` to toggle)
| Action | Effect |
|--------|--------|
| Click any element | Add a note |
| Export button | Copy all annotations as markdown |

### Media Cycler (on slides with image/video galleries)
| Key | Effect |
|-----|--------|
| `Shift + →` | Next image/video |
| `Shift + ←` | Previous image/video |
| `Shift + ↑` | Resume auto-advance |

---

## 🎨 Theme Editor

The Settings slide (hidden slide 0, accessible via the slide grid) includes a full live theme editor:

- **Primary & Secondary Colors** — hex color pickers that update accent colors throughout
- **Background Darkness** — adjust the base background
- **Font Family** — choose from Space Grotesk, Inter, Outfit, JetBrains Mono, Playfair Display, or enter any Google Font name
- **Title Scale** — adjust title font sizes (60%–130%)
- **Tagline Scale** — adjust body text sizes (60%–150%)
- **Paragraph Gap** — control spacing on double line breaks
- **Image Hold Duration** — how long images display before cycling
- **Reset to Defaults** — one click to restore everything

All settings persist via `localStorage` — they survive page reloads and browser restarts.

---

## 🖼️ Media Cycler

The media cycler is a canvas-based image/video gallery with a distinctive pixelated reveal effect.

### How to Use

Set `img: 'MEDIA_CYCLER'` on a case study, then add a cycler IIFE after the SECTIONS loop:

```javascript
// In SECTIONS:
{ title: 'My Project', img: 'MEDIA_CYCLER', ... }

// After the build loop:
(function(){
  const slide = allSlides.find(s =>
    s.querySelector?.('.case-title')?.textContent.includes('My Project'));
  if (!slide) return;
  buildMediaCycler(slide, [
    {type:'image', src:'media/project/photo1.jpg'},
    {type:'image', src:'media/project/photo2.jpg', flipH: true},
    {type:'video', src:'media/project/demo.mp4', loop: true},
  ], {imageDuration: 6000});
})();
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `imageDuration` | `6000` | Milliseconds to hold each image |
| `portrait` | `false` | 9:16 canvas for vertical content |
| `enterDur` | `700` | Slide-in duration (ms) |
| `revealDur` | `1600` | De-pixelation reveal (ms) |
| `exitDur` | `500` | Exit animation (ms) |

### Per-Item Flags

| Flag | Description |
|------|-------------|
| `flipH: true` | Mirror the image horizontally |
| `loop: true` | Loop a video continuously |

### Static Images Get the Effect Too

Case studies with `img: 'path/to/image.jpg'` automatically get the pixelated reveal — no cycler IIFE needed.

---

## 📝 Speaker Notes & Timing

### Adding Notes

```javascript
lesson: {
  title: 'My Lesson',
  notes: 'Key talking point. Pause for effect. Ask the audience a question.'
},
cases: [{
  title: 'Case Study',
  notes: '• Mention the budget\n• Show the before/after\n• This is where the client cried'
}]
```

### Presenter Popup (`N`)

Opens a second window showing:
- Current slide title and notes
- Next slide preview
- Elapsed time (MM:SS)
- Estimated remaining time
- Pacing indicator (🟢 on pace / 🟡 running long / 🔴 over time)

### Duration Estimation

Shown in Settings slide. Calculated from notes:
- **Bullet points** (~20 sec each): short phrases or lines with `-` / `•`
- **Full sentences** (~150 words/minute): prose-style notes
- **No notes**: 30 seconds default
- **Multi-step slides**: +5 seconds per step

---

## 🔗 Multi-Step Slide Animations

```javascript
const mySlide = allSlides.find(s => /* find your slide */);
slideSteps.set(mySlide, {
  current: 0,
  steps: [
    () => { /* Step 1: fade in */ },
    () => { /* Step 2: animate */ },
    () => { /* Step 3: sound */ },
  ]
});
```

Clicking advances through steps before moving to the next slide.

---

## 👁️ Hiding & Parking Slides

### Hiding Slides

**Ctrl/Cmd + Click** a thumbnail in the slide grid:
- Hidden slides show at 30% opacity with dashed border
- Navigation skips them automatically
- Still accessible by direct thumbnail click

### Parking Slides

```javascript
const PARK = [5, 8]; // move these slides to the end
```

---

## 📦 Offline Export

Spatial Deck works from `file://` for most features. For a fully offline experience:

### Quick (covers 90% of cases)

Just copy the folder. `index.html` + `media/` = done.

### Full Offline (3D map + custom fonts)

Use the **📦 Export for Offline** button in Settings, or manually:

```bash
# Download Three.js
mkdir -p lib
curl -o lib/three.module.min.js \
  "https://cdn.jsdelivr.net/npm/three@0.164.1/build/three.module.min.js"

# Update import map in index.html:
#   "three":"https://cdn.jsdelivr.net/..." → "three":"./lib/three.module.min.js"
```

### Including 3D Models (GLTF, OBJ, etc.)

Three.js is already available. Add a rotating model to any slide:

```javascript
const THREE = await import('three');
const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 1, 500);
const renderer = new THREE.WebGLRenderer({ alpha: true });

const loader = new GLTFLoader();
loader.load('media/model.glb', (gltf) => {
  scene.add(gltf.scene);
  function animate() {
    requestAnimationFrame(animate);
    gltf.scene.rotation.y += 0.01;
    renderer.render(scene, camera);
  }
  animate();
});
```

---

## 🤖 AI-Friendly Design

Spatial Deck is designed to be edited by LLMs:

- **Single file** — paste into any context window
- **Config-driven** — change SECTIONS, slides update
- **Semantic HTML** — clear class names
- **Comment landmarks** — `// ── Section Name ──`

### Example Prompts

```
"Add a new lesson about accessibility with two case studies"
"Change the accent color for 2023 to purple"  
"Add speaker notes to all slides"
"Create a media cycler with these 3 images"
"Estimate how long my talk will take"
```

---

## 🏗️ Project Structure

```
spatial-deck/
├── index.html      ← The entire presentation
├── media/           ← Images, videos, GIFs
├── social.html      ← Social sharing card (1200×630)
├── social.png       ← Pre-rendered social image
├── README.md        
└── LICENSE          ← MIT
```

---

## 🎤 Built With Spatial Deck

- **"10 Lessons from 10 Years"** — Alex Coulombe, Harvard XR Conference 2026
- *Add yours — [open a PR](https://github.com/ibrews/spatial-deck/pulls)!*

---

## 📄 License

MIT — use it for anything.

Built with 🎭 by [Alex Coulombe](https://twitter.com/ibrews) at [Agile Lens](https://agilelens.com).

*P.S. Looking for an XR studio that checks all the boxes? [agilelens.com](https://agilelens.com)*
