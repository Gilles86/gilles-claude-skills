---
name: scientific-presentations
description: Build scientific talk decks (conference / symposium / lecture / workshop / job talk) in Gilles's MARP house style — figure-forward slides, gaia theme, the shared CSS style block and helper classes, an outline-first workflow with per-slide speaker notes, and a marp-cli build script. Use this skill whenever the user is preparing slides for a talk, lecture, symposium, workshop, defense, or seminar, mentions MARP / a "deck" / "slides .md", or points at a repo like neuroimaging_encoding_models2026 or computation-in-neuroeconomics-workshop2025 as a template. Pairs with the scientific-figures skill (which makes the individual figures this deck displays).
---

# Scientific presentations, Gilles's house style

The goal is a talk deck that reads like a sequence of **figures with captions spoken aloud**, not a document projected on a wall. Slides are built in **MARP** (Markdown → HTML/PDF/PPTX) with the **gaia** theme and a shared CSS style block. The aesthetic is the talk-sized sibling of the `scientific-figures` house style: high signal, restrained text, every slide anchored by one figure.

This skill is co-developed with Gilles — when a convention here conflicts with what he asks for in the moment, follow him and update this file.

## The one rule that drives everything: figure-forward, minimal text

Every slide is anchored by **one figure** and carries **minimal text** — a short title and, where it helps, **2–3 terse bullets** (phrases, not sentences). The full argument is what Gilles *says*, not what's on the slide. When writing an outline, put that argument in **speaker notes**, not on the slide.

Concretely:
- A slide is a figure + title + (optional) a couple of short bullets. If a slide is mostly text, it's wrong — either it needs a figure or it should be a sparse "pullquote" slide (one bold line, centered).
- Bullets are phrases: "84% of voxels shift up", not "We found that 84% of voxels shifted toward larger numbers in the wide condition."
- Reuse and *extend* a figure introduced earlier rather than adding a wall of new text later. Building intuition on a returning figure beats a fresh dense one.
- Citations are tiny, bottom-of-slide, author + year + venue (see below). They never compete with the figure.
- The panels carry the story (this is the `scientific-figures` "stands alone" rule applied to a room): someone who only sees the figure should get the point. If they can't, fix the figure, don't add text.

When in doubt, cut text and trust the figure + the spoken narration.

## Workflow: outline first, deck second

Don't jump straight to slides. Two phases:

### Phase 1 — slide-by-slide outline (a markdown doc in `resources/`)
A planning document, one entry per slide, that Gilles iterates on before any MARP is written. Each entry has:
- **Slide number + short title**
- **`[FIGURE: ...]` placeholder** — what image anchors the slide. Tag it `🆕` (needs to be made), `♻️` (reuse an existing figure — name the file/repo), or `🎞️` (video/gif).
- **On slide:** the minimal text that will actually appear (title + any bullets).
- **Notes:** the speaker notes — the argument Gilles makes out loud. This is where the real content lives at the outline stage.

Calibrate scope up front with the user — these three answers reshape the whole outline:
- **Duration** (20 / 30 / 45 min → ~1 slide/min is a fine first guess).
- **Audience expertise** (how much primer do they need? what's their home turf? — lean into the part they care about).
- **Deliverable now** (outline only, or outline + repo scaffold).

Don't try to crop figures out of existing PDFs unless asked — leave `🆕`/`♻️` placeholders and let Gilles drop the real images in.

### Phase 2 — build the MARP deck
Once the outline is agreed, write the `.md` deck using the style block and patterns below, and the `build.sh` script. See `references/style_block.md`, `references/build_sh.md`, and `references/snippets.md`.

## Deck structure conventions

- **One self-contained `.md` per talk** (e.g. `talk_name.md`), built by `build.sh`. Workshops with several independent vignettes can use numbered decks (`1_foo.md`, `2_bar.md`).
- **Repo layout:** the deck `.md` at the relevant level, plus `figures/` (final figures), `resources/` (the outline doc, raw assets, source material), `build.sh`, and a `README.md`. Mirror `neuroimaging_encoding_models2026/` (single research talk) or `computation-in-neuroeconomics-workshop2025/` (multi-vignette workshop + exercise notebooks).
- **Section dividers** are HTML comments in the source, so the structure is visible while editing:
  ```
  <!-- ============================================================== -->
  <!-- §5 — VISUAL SEARCH & GAIN FIELDS                                -->
  <!-- ============================================================== -->
  ```
- **Title slide:** suppress footer/pagination (`<!-- _footer: '' -->`, `<!-- _paginate: false -->`), a centered subtitle in italics, and a **triptych** of representative figures across the middle (three `.col`s, each `![height:280px](...)`). Name + venue at the bottom in `text-small`.
- **Closing:** a references slide (or two) in `text-tiny`, multi-column, grouped by theme; then a "Thank you / Questions?" slide (footer + pagination suppressed) with collaborator credits.

## The MARP machinery (gaia)

- Theme `gaia`, `math: mathjax`, `paginate: true`, a `footer:` with the venue.
- A shared **`style:` block** gives the helper classes the whole deck relies on. **Always start from the canonical block in `references/style_block.md`** — it encodes footer/page-number styling, tightened headings, the `.two-col` grid with preset splits, and the text-size classes. Copy it verbatim into a new deck.
- Slide titles use `##` (h2) in the research-talk decks; the style block tightens h1/h2 spacing so content gets vertical room.

### Helper classes you will use constantly (defined in the style block)
- **`.two-col`** + `.col` — the workhorse layout (text on one side, figure on the other). Width presets: `.two-col--50`, `.two-col--30-70`, `.two-col--70-30`.
- **`.center`**, **`.vcenter`**, **`.slide-vcenter`** — horizontal / vertical / full-slide centering (use `.vcenter` inside a `.col` to center a figure against text).
- **Text sizing:** `.text-medium` (30px) · `.text-mediumsmall` (27px) · `.text-small` (24px) · `.text-twenty` (20px) · `.text-tiny` (16px) · `.code-small` (14px). Default body is large; step *down* explicitly when a slide genuinely needs more.
- **`.pullquote`** (36px italic) — for the bold one-line punchline slides.

### Sizing images
- Use `![width:NNNpx](...)` / `![height:NNNpx](...)` to size — **px only** (`vh`/`vw` in the `![...]` hint are silently ignored → natural size, often huge); in two-col layouts, `.col img { max-width/height: 100%; object-fit: contain }` keeps them in their column.
- Videos: raw `<video controls autoplay loop>` — **size with the `width=` attribute, not inline `style`** (MARP strips `style` from `<video>`). Build with `--allow-local-files`.

### Positioning things exactly (when flow layout won't cooperate)
Two-col + `![bg ...]` cover most slides, but when you need a figure, label, or text box at a *specific* spot, stop fighting the markdown flow and place it directly. The slide is a fixed **1280×720** pixel canvas (center `640,360`), so a typed coordinate is stable across preview/PDF/projector. Drop one `<div style="position:absolute; top:…; left:…">`, zero the section padding for that slide with `<style scoped>section{padding:0!important}</style>` (so coords = true pixels), and watch it in `./build.sh watch`. Patterns for absolute placement, arrows/labels glued to a figure, floating text over a full-bleed figure, corner-by-alt-text, caption-over-split-bg, and panel grids are in **`references/positioning.md`**; the `.grid2`/`.grid3` (used as `<!-- _class: grid2 -->` + `<div class="panels">`) and `img[alt~="top-right"]` helpers are already in the style block.

### Rendering gotchas (read before fighting a layout)
The traps that *actually* bite (all verified against marp-cli output):
- **Blank lines inside every layout `<div>`** (after `<div ...>`, before `</div>`). Without them markdown-it parses the block as raw HTML and **strips the inner tags' attributes** — your `style`/`width` silently vanish. This is the #1 cause of "my layout didn't apply" (e.g. a flex wrapper that doesn't center, a video that ignores its width).
- **`<video>` drops `style`** — size it with the `width=` attribute; center with `.center` (video is inline-level) or a flex wrapper (with blank lines).
- **`![h:..vh]` is ignored** (falls through to alt text) — image size hints must be **px**.
- **Positioning works as documented** — the earlier "gotcha" that `_class` only emits `data-class` was wrong: `_class: foo` emits a real `class="foo"`, so `section.foo{}` matches, and absolute pixel placement is reliable on a `.bleed` slide (which zeroes gaia's 70px padding and sets `position:relative`). Use `positioning.md`'s coordinate toolkit; the only reason a `bottom:0` element floats high is a missing `position:relative` + the unzeroed padding.

`positioning.md` (how to place) and `marp_layout_gotchas.md` (what breaks + asset prep) are companions — consult them whenever a position/size doesn't take.

## Citations

- Inline, on the slide, in `text-tiny`, centered or bottom-of-column: **Author(s) (Year). *Venue* vol: pages.** — e.g. `<span class="text-tiny">Wei & Stocker (2017). *Nat Neurosci* 20: 1314–1321.</span>`.
- For a chain of own work, list compactly: `Author, de Hollander et al. (2023, 2024, 2026)`.
- Full reference slides at the end, `text-tiny`, grouped (framework / domain / own work).

## Building

`build.sh` wraps `marp-cli` from the `marp` conda env (`~/mambaforge/envs/marp/bin`). Subcommands: `html` (default), `pdf`, `pptx`, `png`, `watch` (live server), `all`. Always `--allow-local-files` (needed for images/video). Template in `references/build_sh.md`. To preview while editing: `./build.sh watch`.

## Relationship to scientific-figures

This skill governs the **deck**; `scientific-figures` governs the **individual figures** on it. When a slide needs a `🆕` figure made, switch to `scientific-figures` for the plotting house style — and remember its rule to **regenerate at slide size** (bigger fonts, ~14–18 pt; don't shrink a paper figure onto a slide).

## Reference files
- `references/style_block.md` — the canonical gaia `style:` block to paste into a new deck.
- `references/build_sh.md` — the `build.sh` template + the `marp` conda env setup.
- `references/snippets.md` — copy-paste slide patterns (title triptych, two-col text+figure, pullquote, video, citation, references slide).
- `references/positioning.md` — how to place things precisely: the fixed 1280×720 pixel canvas, absolute-`<div>` placement, arrows/labels glued to a figure, full-bleed figure + floating text, background-image syntax, corner-by-alt-text, caption-over-split-bg, panel grids. The "how to place" companion to the gotchas file.
- `references/marp_layout_gotchas.md` — rendering quirks & asset prep: the blank-lines-inside-divs rule (or attributes get stripped), `<video>` drops `style` (size via `width=`), `![h:..vh]` ignored (use px), `**bold**` not parsed in inline divs, EXIF baking, transparent-margin autocrop, transparent→white compositing, and build/shell traps (node PATH, `cp -i`). The "what breaks" companion to `positioning.md`.
