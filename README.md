# Spatial Deck

> A self-contained, single-file presentation framework for live talks.
> Designed for projector display, wireless clickers, and AI-collaborative editing.

**Live demo:** [https://ibrews.github.io/spatial-deck/](https://ibrews.github.io/spatial-deck/)

Spatial Deck is one HTML file. No build step. No dependencies. No framework. Open it in any browser, edit one config object at the top, and you have a polished interactive talk that runs anywhere — your laptop, a 1920×1080 projector, a phone, GitHub Pages, anything that serves an HTML file.

It came out of preparing a closing keynote for the [Harvard XR Conference 2026](https://harvardxr.com), where the speaker needed:

- Beautiful slides without learning Keynote/PowerPoint conventions
- Modular content that could be edited collaboratively with an AI agent
- A way for teammates to leave visual feedback on a live URL
- Compatibility with wireless presenter clickers
- Easy navigation across 30+ slides during dry runs
- A self-contained file that could be shared without infrastructure

The full result is at [github.com/ibrews/harvardxr-keynote](https://github.com/ibrews/harvardxr-keynote). This repo is the **starter kit** — that talk's framework with all the brand-specific content stripped out, ready to fork.

---

## Quick Start

```bash
git clone https://github.com/ibrews/spatial-deck.git
cd spatial-deck
open index.html        # macOS — opens in your default browser
# OR: python3 -m http.server 8080  →  http://localhost:8080
```

Then edit the `SECTIONS` array at the top of `index.html`. Reload the browser. That's the entire workflow.

To deploy: push to a GitHub repo, enable Pages on the `main` branch, share the URL. There is no build pipeline.

---

## What you get

### Slide types (auto-generated from config)

| Type | Purpose |
|---|---|
| **Cover** | Title slide with speaker card |
| **Case study** | Image + title + 1-3 bullet points (left-right layout) |
| **Lesson** | Big takeaway slide with title, tagline, and optional reference tags |
| **Bonus** *(optional)* | Wildcard slide that comes after the main sections |
| **Map** | Animated constellation showing every section + lesson, with click-to-jump nodes |
| **Closing** | Thank-you slide with contact pills |

### Navigation

- **Arrow keys**, **Space**, **Page Down/Up**, **N/P** — all advance/retreat
- **Wireless clickers** — anything that emits PageDown/PageUp works
- **Touch swipe** — works on phones/tablets
- **Slide grid** at the bottom of the screen — hover the bottom 38px to reveal a horizontally-scrolling thumbnail strip of every slide. Click any thumb to jump. Active slide auto-scrolls into view.
- **Map slide** — every section appears as a node on a circle; click any node to jump to that lesson
- **Home / End** — first / last slide
- **`H` key** — toggle **presentation mode**: hides every UI chrome element (counter, brand, nav arrows, slide grid, annotate/move toggles, panels) so the projector shows only the slide content. Press `H` again to bring everything back.
- **URL hash routing** — append `#5` to any URL to drop a viewer directly on slide 5. Share `https://your-site/#10` and the audience lands on slide 10. The URL hash auto-updates as you navigate so any slide is bookmarkable.

### Annotation system (the differentiator)

Spatial Deck includes two collaboration modes for working with an AI agent on the talk:

**📝 Annotate Mode** (toggle with `A` or the top-left button)
- Click any element on the page → leave a note ("make this bigger", "wrong color", "punchier wording")
- Notes are saved to `localStorage` with the element's CSS selector + slide context
- Click "📋 Copy All" → exports as markdown ready to paste into Claude/ChatGPT/Cursor
- The agent reads the markdown, finds the element in the source, makes the change

**✋ Move Mode** (toggle with `M` or the orange button) — full transform engine
- **Drag** any element to translate it
- **Shift + drag** to scale (drag away from element center to grow, toward to shrink)
- **Alt/Option + drag** to rotate (drag in a circle around element center)
- Works on **SVG paths and lines too** — paths transform via standard CSS so the same controls work on any visual element
- **Undo / Redo** — `Cmd/Ctrl + Z` to undo, `Cmd/Ctrl + Shift + Z` to redo. Onscreen Undo/Redo buttons in the move-mode HUD next to the toggle.
- 50-action history stack with standard editor semantics (new action clears the redo branch)
- Each annotation captures the full transform: `TRANSFORM translate Δ(+30px, -20px) · scale ×1.20 · rotate 15°`
- The element stays where you put it so you can see your layout
- Perfect for "the monocle should be 30px to the left, scaled up 20%" feedback that's faster to *do* than to describe

The export workflow is just clipboard markdown — no API key, no MCP server, no React. Works on plain HTML by design.

### Designed for projector display

All typography uses `clamp(min, vw-based, max)` calibrated for 1920×1080 projectors:
- Lesson titles up to 6.2rem (~100px)
- Case study bullets up to 1.3rem (~21px)
- Cover title up to 8.5rem (~136px)

Smaller windows scale down naturally. Phones get a column-stacked layout via `@media(max-width:900px)`.

---

## The Config

The entire content of your talk lives in one JavaScript object at the top of `index.html`:

```js
const SECTIONS = [
  {
    year: 2016,            // Or 'CH 1', or any string label
    accent: 'teal',        // teal | purple | amber | rose
    cases: [
      {
        title: 'Project Name',
        subtitle: 'Short hook line',
        img: 'https://...',  // Or '' for a gradient placeholder
        bullets: [
          'A specific, concrete observation',
          'A second beat that builds on the first',
          'The detail that earns you the right to make the lesson land',
        ],
      },
    ],
    lesson: {
      title: 'Your Lesson Title.\nUse \\n for a Line Break.',
      tagline: 'One paragraph that distills what you learned.',
      tags: 'Optional · References · Or · Project · Names',
    },
  },
  // Add as many sections as you want — engine handles arbitrary length
];

// Optional bonus slide. Set to null to omit.
const BONUS = {
  year: 2026,
  title: 'A Light, Memorable Closer.\nLeave Them Smiling.',
  tagline: 'Your bonus slide is the punchline.',
};
```

That's it. The engine reads `SECTIONS`, generates all the case study and lesson slides, builds the slide grid, builds the constellation map, and wires up the tracker — all from the data.

---

## Design Philosophy

### Why one file?

A presentation should outlive its tooling. Keynote files break across versions. PowerPoints lose fonts. Reveal.js needs node_modules. A single HTML file with inline CSS and JS will still open in 2050.

### Why JavaScript config instead of Markdown / YAML?

You want the config in the same file as the engine because **the engine is the spec**. If you're going to customize colors, timing, or layout, you don't want to learn a separate template language — you just edit JavaScript and CSS in the same place.

For non-developers: the config is mostly strings, arrays, and objects. The shape is simple enough that an AI agent can edit it confidently.

### Why no React/Vue/framework?

Frameworks are great for apps. They're overkill for a talk that runs for 30 minutes once. They also rule out:
- Sharing the talk as a single attachment
- Hosting on a static file server with no build
- Editing the talk on a plane with no internet
- Letting a non-developer edit the deck without setting up node

The **no-framework constraint** is what made Agentation incompatible with this use case (it requires React 18) and forced us to build our own annotation system. The annotation system that came out of that constraint turned out to be the best feature.

### Why CSS @keyframes instead of CSS transitions?

Subtle but important: CSS transitions on absolute-positioned elements have a long history of edge cases where the transition silently fails to fire (TDZ issues, reflow timing, etc). CSS `@keyframes` animations are rock-solid and don't depend on the browser noticing a style change. The slide system here uses keyframes for that reason.

### Why a constellation map at the end?

Most decks just stop. The map slide is a recap mechanism: zoom out, see every lesson at once, click any node to revisit. It also looks cool, which matters for closing keynotes.

### Why the slide grid at the bottom?

Because navigating from slide 2 to slide 30 with only arrow keys is misery during a dry run. The hover-to-reveal pattern keeps it out of the way during the actual talk.

---

## Customizing

### Colors / theme

Edit the CSS variables at the top of the `<style>` block:

```css
:root {
  --bg: #060810;
  --teal: #00d4ff;
  --purple: #a78bfa;
  --amber: #f59e0b;
  --rose: #f43f5e;
  --text: #f0f4ff;
  --dim: rgba(240, 244, 255, .45);
  --font: 'Space Grotesk', system-ui, sans-serif;
}
```

The four accent colors are tied to the `accent: 'teal'|'purple'|'amber'|'rose'` setting on each section. Add more colors by editing both the variables and the `.accent-*` CSS rules.

### Typography

The font is loaded from Google Fonts (`Space Grotesk`). Swap the `<link>` tag in the `<head>` for any other Google Font and update `--font`.

### Background

The animated background has three layers (defined in `.bg-gradient`, `.grid-floor`, and `#stars`):
- A radial gradient
- Optional perspective grid floor (currently disabled in this starter — add the markup back if you want it; see the [keynote repo](https://github.com/ibrews/harvardxr-keynote) for the full version)
- A canvas of twinkling stars

Remove or replace any of these without affecting the engine.

### Optional brand-mark overlay on the map

If you have a transparent PNG of your logo, point `LOGO_URL` at it (in the map animation section) and it'll fade in at the center of the constellation as a watermark when the map slide ends.

### Avatar / mascot

The original Harvard XR talk had a walking-avatar mascot that traveled around the constellation as you advanced through the talk, with a "fist pump" celebration on the final map. That code was stripped from this starter to keep it clean — see the [full keynote repo](https://github.com/ibrews/harvardxr-keynote) if you want to reuse it.

---

## File structure

```
spatial-deck/
├── index.html      # The entire framework + demo content. Edit SECTIONS at top.
├── README.md       # This file.
├── LICENSE         # MIT.
└── .gitignore      # Standard.
```

That's it. There is no `package.json`, no `node_modules`, no build output, no `dist/`. The whole repo is one HTML file plus docs.

---

## Working with an AI agent

Spatial Deck was built specifically to be edited collaboratively with Claude, Cursor, ChatGPT, or any agent that can read & edit a file. The annotation system makes the loop tight:

1. You: open the deck in a browser, press `A`, click an element, type a note, hit "Copy All"
2. You: paste the markdown into your agent's chat
3. Agent: reads the selectors and notes, edits `index.html`, pushes
4. You: reload the browser, see the change

Or with Move Mode:

1. You: press `M`, drag the element where you want it
2. You: press `A`, hit "Copy All", paste into chat
3. Agent: reads the `MOVE by Δ(...)` deltas and converts them to actual CSS positions

This is *much* faster than describing positional changes in English. The agent gets exact pixel deltas instead of "move it down a bit and to the left."

### Suggested handoff prompt for teammates

```
I'm editing a Spatial Deck presentation at <YOUR_REPO_URL>.
The whole talk is one HTML file (index.html) with a SECTIONS config
at the top of the <script> tag. Each section has cases[] (case study
slides) and a lesson (the takeaway slide). The engine generates
everything from this config. To change content, edit the config.
To change colors, edit the CSS variables. To change layout, edit the
CSS rules near the top of <style>.

I'll paste annotations from the deck below. Apply them and push.
```

---

## Credits

Spatial Deck was built by [Alex Coulombe](https://agilelens.com) and Claude (Opus 4.6) in April 2026 while preparing the closing keynote for the [Harvard XR Conference](https://harvardxr.com). The engine is a stripped-down version of the [`harvardxr-keynote`](https://github.com/ibrews/harvardxr-keynote) project — which is the best place to look if you want to see the framework used for a real talk with full content.

If you use this for a talk, [Alex would love to know](https://agilelens.com).

## License

MIT. Do what you want. A credit link back to this repo if you use it for something public is appreciated but not required.
