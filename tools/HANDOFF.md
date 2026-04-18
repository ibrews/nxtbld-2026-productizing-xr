# Spatial Deck — Fleet Importer Roadmap (Handoff for Fresh Session)

**Target model:** Sonnet 4.6 is plenty for most of this. The work is formulaic — scaffold a Python script, call a fleet endpoint, validate JSON, splice into `index.html`. Reserve Opus for the items explicitly flagged as needing judgment (narrative, UX, layout intent). Fast Mode works fine too.

**Read first:**
- [README.md § 🤝 Claude Design Handoff](../README.md) — user-facing description of what exists
- [tools/fleet_client.py](fleet_client.py) — 90-line Ollama wrapper, already battle-tested
- [tools/import_tokens.py](import_tokens.py) + [tools/import_pptx.py](import_pptx.py) — the two shipped importers. Mimic their structure.
- [intelligence/research/parallel-builds/2026-04-17-claude-design-vs-spatial-deck.md](../intelligence/research/parallel-builds/2026-04-17-claude-design-vs-spatial-deck.md) — strategic context on why this track exists

## What's already shipped

| Feature | How it works | Commit |
|---|---|---|
| **Design-token import** | Any CSS/JSON/prose → `llama3.1:8b@Sam` normalizes to fixed schema → regex-validates hex → patches `:root{}` in `index.html` | cb9199e |
| **PPTX import** | `python-pptx` extracts text/images deterministically → `llama3.1:8b@Sam` rewrites body copy into tight bullets → merger splices between `// ── IMPORTED START ──` sentinels | ee415a1 |
| **Markdown import** | Regex parses `#`/`##`/`-`/`![]()`/`>` deterministically → optional `--tighten` via `llama3.1:8b@Sam` with `qwen3:8b@MBP` fallback → merger splices chapter | (this PR) |
| **HTML import** | BeautifulSoup chunks by `<section>`/headings → `qwen2.5-coder:14b@Archie` normalizes to `{title,subtitle,bullets}` with `qwen3-coder:30b@MBP` fallback → images (incl. `data:` URIs) land in `media/import-*/` | (this PR) |
| **PDF import** | `pdfplumber` per-page text sorted by y/x → `llama3.1:8b@Sam` normalizes → `page.crop().to_image()` for embedded rasters | 3a10a79-ish |
| **Slide linter** | Node subprocess evals SECTIONS as data → static checks (title/bullet length, dup titles, orphan numbers, empty taglines) → optional `--llm` semantic pass via `llama3.1:8b@Sam`. Never mutates. | acd4ff6 |
| **Timing estimator** | Same extractor → 150wpm/20s-per-bullet formula → markdown/JSON report with pacing traffic-light against `--target`; `--generate` drafts notes via `llama3.1:8b@Sam` | 3a10a79 |
| **Alt-text generator** | Vision via `gemma3:12b@Lenny` over local image paths in SECTIONS. JSON patch output only. `--scan-media` lists orphans. | 3451dcc |
| **Palette extractor** | Pillow + pure-Python k-means++ → hue/luminance map to token schema, synth missing accent hues from primary. Optional `--vibe` via Lenny vision. Round-trips through `import_tokens.py`. | 1ad39d4 |
| **SessionStart git-freshness hook** | Warns if repo is behind origin (unrelated to importers, but installed same day) | KB 73f067f9 |

## Fleet endpoints (confirmed working 2026-04-18)

```
sam    100.127.46.63:11434   llama3.1:8b        — structured JSON, classification (fleet winner for these)
archie 100.103.192.41:11434  qwen2.5-coder:14b  — code parsing, HTML/XML
lenny  100.78.179.55:11434   qwen3-coder:30b, gemma3:27b — code-gen, design/visual
mbp    100.95.59.11:11434    qwen3-coder:30b    — code-gen fallback
```

Fort is offline (has been 5+ nights as of 2026-04-17). Sam can be flaky — `Connection refused` means Ollama daemon stopped; the machine is fine. Route to Archie's `llama3.1:8b` as fallback.

## What we learned (apply to every new importer)

1. **Single-pass only.** The fleet collapses on "revise this JSON" prompts. If parse fails, re-prompt with a *different* prompt, never "please fix."
2. **Validate structure, not semantics.** Hex regex, enum check, required-keys check. Trust the model's judgment on the text itself — it's better than you'd expect.
3. **Deterministic extraction first, LLM for cleanup.** `python-pptx` handles XML. BeautifulSoup handles HTML. The LLM only rewrites prose or classifies.
4. **Fall back silently to raw.** If LLM normalization fails, use the raw extracted text. Don't block the user on model reliability.
5. **Sentinel-based splicing is idempotent.** `// ── IMPORTED START ──` / `// ── IMPORTED END ──` lets you re-import as many times as you like.
6. **Match the existing `js_string()` emitter in merge_sections.py** — it handles backslash/quote/newline escaping correctly. Don't reinvent.
7. **No JSON mode in Ollama.** Always append `"Return ONLY valid JSON. No prose."` and parse defensively (`_extract_json` in fleet_client handles fences, stray prose, `<think>` blocks).
8. **Per-slide chunking for Sam.** 16GB RAM machine — don't send entire files. One slide per call, parallelize across machines if speed matters.

## Roadmap — FLEET-FIRST (ship with minimal Claude oversight)

### ~~A. Standalone-HTML importer~~ ✅ SHIPPED
See `tools/import_html.py`. Structural-selector chunking with heading fallback; Archie primary, MBP fallback; `data:` URIs decoded to `media/`.

### ~~B. Markdown importer~~ ✅ SHIPPED
See `tools/import_md.py`. `#`/`##`/`-`/`![]()`/`>` convention, deterministic parse, optional `--tighten`.

### ~~C. Slide linter~~ ✅ SHIPPED — `tools/lint_deck.py`
### ~~D. Image alt-text generator~~ ✅ SHIPPED — `tools/gen_alt_text.py`
### ~~E. PDF importer~~ ✅ SHIPPED — `tools/import_pdf.py`
### ~~F. Speaker-note timing estimator~~ ✅ SHIPPED — `tools/estimate_timing.py`
### ~~G. Palette from reference image~~ ✅ SHIPPED — `tools/extract_palette.py`

## Roadmap — CLAUDE-FIRST (judgment / UX / reasoning)

### H. `component:` registry *(architecture refactor)*
**Why Claude:** Design-space exploration. SECTIONS is config; this adds a new slide-type layer. Needs thinking about extensibility vs the project's "single-file, no-build" ethos.
**Starting point:** Consider whether `component:` should be a string enum matching a JS dispatch table, or a template literal evaluated at build. Trade-offs matter.

### I. 2–3 new slide layouts
**Why Claude:** CSS + visual judgment. Possible additions: split-screen (text left, media right, 50/50), full-bleed media with overlay caption, three-column comparison.
**Starting point:** Look at `case-slide` and `lesson-slide` classes in `index.html` as templates; clone + modify.

### J. Keyframe animation auto-generation from prose intent
**Why Claude:** "Make the title fade in then the bullets cascade" → WAAPI keyframes on the right elements. Intent parsing + DOM mapping is genuinely hard for local models (no reasoning >6/10 on the fleet).
**Starting point:** Spatial Deck's existing keyframe system is at `// ── Keyframe Animation System ──` in index.html. Extend the `◆ KF` button flow.

### K. Narrative coach / slide-reorder suggester
**Why Claude:** Requires understanding story arc. Given a SECTIONS array, suggest reorderings, flag "setup missing before payoff," identify missing transitions.

### L. Importer UI panel inside the deck
**Why Claude:** Needs UX thought. Could add a hidden admin slide that takes drag-and-drop `.pptx` / `.css` and runs the Python tools server-side (or WASM-side for offline).
**Watch out for:** Violates the "no build process, one file" core promise if done wrong. Probably needs to stay CLI-only.

## Roadmap — HYBRID

### M. End-to-end "Claude Design → Spatial Deck" demo
Combine A + the existing token importer. Fleet extracts structure, Claude writes the README/demo narrative + social card. Good candidate for a PR that demonstrates the companion-mode positioning publicly.

### N. Multi-deck merge
Fleet extracts SECTIONS from N source decks, Claude resolves overlap/conflicts and picks a narrative order. Pure Python for the merge; Claude for the editorial pass.

## Gotchas the fresh session should know

- **`index.html` is densely packed** — long lines, minimal whitespace. Match the existing style. CLAUDE.md in `.claude/` enforces this.
- **Don't add a build step.** No npm, no webpack, no bundler. It's a hill to die on.
- **Commit after every shipped slice.** Local-only. Only push when the user asks (`git push origin main`). Previous session pushed without asking — the user didn't mind but it's not the default.
- **The user's `index.html` often has uncommitted edits.** Leave them alone. Dry-run importers or use `--html /tmp/copy.html` for testing.
- **Node is available** (`/opt/homebrew/bin/node`) for JS syntax validation of the patched `index.html`. Use `node --check`.
- **`python-pptx` is installed** via `pip3 install --user --break-system-packages`. `beautifulsoup4` and `pdfplumber` are not yet.
- **Every importer should have a `--dry-run` flag** (tokens) or a separate merge step (pptx). Never overwrite `index.html` in one shot without the user seeing output first.
- **KB at `~/knowledge/`** has the fleet roster (`departments/engineering/infrastructure-overview.md`) and the nightly eval manifest (`fleet/delegation-manifest.md` — re-check before pipeline building).
- **Fleet routing is a moving target.** Fort is offline today; llama3.1:8b also exists on Archie. Check `curl http://<ip>:11434/api/tags` before committing to an endpoint.

## Suggested first move for the fresh session

All seven fleet-first items (A–G) have shipped. Remaining work is CLAUDE-FIRST territory (H–L, M–N) — judgment, UX, narrative. Don't start those speculatively; wait for a real user asking for them.

Good next moves if the user greenlights more fleet work:
- A **peer-review harness**: given a chapter JSON, have two different fleet models critique the output and merge-vote. Cheap observability over the whole importer pipeline.
- A **reverse-importer**: `tools/export_sections.py` → emit a clean `.md` / `.html` / `.pptx` from the current SECTIONS. Symmetric with the existing importers, useful for handoff the other way.
- **Deck diff**: given two SECTIONS arrays (e.g. before/after a template merge), summarize what moved, what changed, what's new.
