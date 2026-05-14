# Review Needed

## Bonus slide (#48) — monocle conflict, 2026-05-14

Two parallel sessions worked on the same 3D-monocle IIFE on slide #48 (`(function(){ ... // 3D Monocle on Bonus slide ... })()`) at the same time, with very different intents:

**Pushed (commit `76c4929`):** Expand the existing Three.js 3D monocle frame
- Container 300px → 380px, repositioned (`left:73.5%; top:24%`)
- Canvas scale 0.57 → 0.62
- Camera z 8 → 11
- Group `position.y = 0.6` to recenter content so the cord fits
- Goal: same 3D monocle, just bigger frame so the cord doesn't get cropped

**Parallel session's stash (`stash@{0}: On main: parallel-pipe-a-wip-round2`):** Wholesale replace the 3D Three.js monocle with an SVG monocle copying the slide-4 (orbit) construction
- Comment introduced: "SVG Agile Lens Monocle on Bonus slide — same construction as slide 4 (orbit), scaled bigger to engage with this slide. Replaces the prior 3D Three.js corner monocle."
- ~67 inserts / 108 deletes in the same IIFE
- Also has unrelated `pipe-a` mouse-reactive + ripple + product-pill work

**Decide which to keep**, then either:
- Pop the stash and resolve the IIFE conflict manually (`git stash pop` — current state of `stash@{0}`), or
- Drop the stash with `git stash drop stash@{0}` if you want to keep my Three.js expansion as-is.

The parallel session's `pipe-a` changes (slide #44 amorphous variant — mouse-reactive translation, edge vignette, click ripple, prod-as-pill styling) are also in that stash and are not in conflict with anything pushed. Worth preserving separately if you drop the stash — they can be re-extracted from `stash@{0}^{tree}:index.html`.
