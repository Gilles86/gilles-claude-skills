---
name: scientific-presentations
description: Build scientific talk decks (conference / symposium / lecture / workshop / job talk) in Gilles's MARP house style — figure-forward slides, gaia theme, the shared CSS style block and helper classes, an outline-first workflow with per-slide speaker notes, drop-in UZH corporate-design front matters, and a marp-cli build script. Use this skill whenever the user is preparing slides for a talk, lecture, symposium, workshop, defense, or seminar, mentions MARP / a "deck" / "slides .md", or points at a repo like neuroimaging_encoding_models2026 or computation-in-neuroeconomics-workshop2025 as a template. Pairs with the scientific-figures skill (which makes the individual figures this deck displays).
---

# Scientific presentations, Gilles's house style

The goal is a talk deck that reads like a sequence of **figures with captions spoken aloud**, not a document projected on a wall. Slides are built in **MARP** (Markdown → HTML/PDF/PPTX) with the **gaia** theme and a shared CSS style block. The aesthetic is the talk-sized sibling of the `scientific-figures` house style: high signal, restrained text, every slide anchored by one figure.

This skill is co-developed with Gilles — when a convention here conflicts with what he asks for in the moment, follow him and update this file.

## Before anything else: you do not run marp

**Gilles runs `./build.sh watch` and he is the visual verifier.** He has `http://localhost:8080/<deck>.md` open in a browser and it reloads the moment you save. You edit the `.md` and tell him which slide to look at. **Do not render PNGs to check a layout** — it is far slower than he is.

What is actually measured on this machine: an **HTML build takes ~1.4 s**, but an **image export takes over 3 minutes for a single slide**. That cost is in the image export itself, not in the browser — it was reproduced with `--browser firefox` as well as Chrome, so *switching browsers is a tested non-fix; do not try it again.* Running several marp processes at once makes it far worse (six concurrent turned 1.4-second builds into 5-minute hangs and one sat stuck for over an hour, with his preview dead throughout), but concurrency was never the whole story.

Treat rendering as unavailable, not merely discouraged: even a one-slide export blew past three minutes, so there is no working "quick peek". If you attempt one anyway, **write the temp deck outside the watched directory** — a scratch file dropped next to the deck is picked up and converted by his watch server too (temp files have been observed appearing in its file index), which is the most likely remaining cause of the hangs and is *untested*. One process, never the full deck, `ps aux | grep '[m]arp/bin/marp'` before and after, and **never kill a `--watch --server` process**. Delegating render work to a subagent is a known hazard — one was told "excerpts, strictly sequential" and still launched parallel full-deck exports.

When you truly need eyes on a slide, the cheap options are: ask Gilles to paste a screenshot (he already has it open), or drive his existing browser via the Claude-in-Chrome extension if it is connected — neither starts a new browser.

Instead of rendering, run the ~0.1 s checks in **`references/verification.md`**: slide count + per-slide titles, every `figures/…` path resolves on disk, `<div>` balance, and a lint for the layout traps below. The figure check caught a genuinely broken deck when an image was renamed underneath us.

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
- **Closing:** a references slide (or two) in `text-tiny`, multi-column, grouped by theme; then a "Thank you / Questions?" slide (footer + pagination suppressed) with collaborator credits. Note the title and closing slides often share *identical* markup — an exact-match string replace silently hits both; use `.replace(old, new, 1)` or edit by slide index.
- **Bullet-only slides: `.measure` + `.slide-vcenter`, always.** Full-width bullets run ~75-90 characters per line, which is too wide to read; `.measure` (820px) brings it to ~55-60, left-aligned. Vertically centre it or a short list sits jammed under the title. Slides with a figure or `two-col` are already constrained — do not add `.measure` there.
- **List + conclusion → evidence left, verdict right.** Gilles's default: bullets in a left column, the conclusion in a narrow right column (`two-col--70-30`), *not* a centred line underneath. Pattern in `references/snippets.md`.
- **Progressive reveal: use fragments first.** Marp *does* have a reveal — change the bullet marker from `-` to `*` (or `1.` to `1)`) and items appear one click at a time. Inactive fragments are `visibility:hidden`, so **nothing reflows**; duplicated slides re-lay-out each step and visibly jump. `data-marpit-fragment="N"` also works written by hand on any element (a punchline, a figure). Fragments are **HTML-only** — PDF shows them all — and they reveal without restyling. Duplicate slides *only* when a step transforms earlier content (`.dim`, font stepping, as in the crowding-is-the-point list), and then pin the row height so the figure beside it does not drift. Full detail: `references/marp_layout_gotchas.md`. **Builds cost no talk time**, so use them freely.
- **Speaker notes are HTML comments** on the slide — they show up in MARP's presenter view. Write what Gilles *says*, one per slide. **Avoid `--` inside a comment**; it can terminate the comment early.
- **Mark cut candidates, don't delete them:** `<!-- CUT CANDIDATE (reason) -->` above the slide, plus a cut plan in the deck `README.md` (cut in advance / cut live if long / do not cut). Shortening the talk is then one delete and nothing is lost.

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
- **Landscape figure in a column → size by `width:`.** The style block composites images on white (`section img { background-color:#fff }`), so height-sizing a landscape figure inside a narrower column letterboxes it and those bands show as bright slabs against the slide. Height-sizing is for **portrait** figures and full-width ones.
- **Full-width figure + a caption line: keep the image at or under ~395px** of height, or the caption lands on the footer.
- Videos: raw `<video controls autoplay loop>` — with `--html` on, both `width=` and inline `style` survive. Build with `--allow-local-files`; video plays in the HTML output only.

### Positioning things exactly (when flow layout won't cooperate)
Two-col + `![bg ...]` cover most slides, but when you need a figure, label, or text box at a *specific* spot, stop fighting the markdown flow and place it directly. The slide is a fixed **1280×720** pixel canvas (center `640,360`), so a typed coordinate is stable across preview/PDF/projector. Drop one `<div style="position:absolute; top:…; left:…">` and zero that slide's section padding with `<style scoped>section{padding:0!important}</style>` so coords are true pixels. Patterns for absolute placement, arrows/labels glued to a figure, floating text over a full-bleed figure, corner-by-alt-text, caption-over-split-bg, and panel grids are in **`references/positioning.md`**; the `.panel-grid-2`/`.panel-grid-3` wrapper classes and the `img[alt~="top-right"]` corner helpers are already in the style block.

### Rendering gotchas (read before fighting a layout)
The traps that *actually* bite (all verified against marp-cli output) — `positioning.md` (how to place) and `marp_layout_gotchas.md` (what breaks + asset prep) carry the rest:
- **Pass `--html` to every marp call** (it's in the house `build.sh`). Without it marp-cli strips inline `style`/`id` from your tags and every flex/absolute layout collapses; `class` and `![w:..]` survive, which is exactly why the bug hides. Front-matter `html: true` does **not** work. This was also the real cause behind two earlier, wrong diagnoses — that blank lines strip attributes, and that `<video>` drops `style`. Both were the missing flag.
- **Blank lines inside every layout `<div>`** (after `<div ...>`, before `</div>`) so the markdown *inside* it is parsed. Without them it leaks as literal text — and `**bold**` on a single-line inline div renders literal asterisks.
- **`![h:..vh]` is ignored** (falls through to alt text) — image size hints must be **px**.
- **`<style scoped>` works and does not leak** to other slides (marp scopes the selector to that one section) — the right tool for a per-slide padding override. `_class: foo` also emits a real `class="foo"`, so `section.foo{}` matches; the old "only `data-class`" note was wrong.
- **Don't use `>` blockquotes for quoted remarks** — gaia adds its own decorative quote glyphs, which double up with your quotes. Use typographic quotes in a styled `<div>` (`snippets.md`).

## Citations

- Inline, on the slide, in `text-tiny`, centered or bottom-of-column: **Author(s) (Year). *Venue* vol: pages.** — e.g. `<span class="text-tiny">Wei & Stocker (2017). *Nat Neurosci* 20: 1314–1321.</span>`.
- For a chain of own work, list compactly: `Author, de Hollander et al. (2023, 2024, 2026)`.
- Full reference slides at the end, `text-tiny`, grouped (framework / domain / own work).

## Building

`build.sh` wraps `marp-cli` from the `marp` conda env (`~/mambaforge/envs/marp/bin`). Subcommands: `html` (default), `pdf`, `pptx`, `png`, `watch` (live server), `all`. Always `--html --allow-local-files` (the first keeps inline `style`/`id`, the second embeds images/video — both mandatory). Template in `references/build_sh.md`. `./build.sh watch` is **Gilles's** terminal, not yours — see the top of this file.

## UZH branding

For a talk given as UZH, paste `references/uzh_frontmatter_corporate.yml` over the deck's front matter — the body needs no edits. `_light` and `_contrast` variants, the verified UZH palette and typeface, and what is CD-specified vs. invented: `references/uzh_house_style.md`.

## Relationship to scientific-figures

This skill governs the **deck**; `scientific-figures` governs the **individual figures** on it. When a slide needs a `🆕` figure made, switch to `scientific-figures` for the plotting house style — and remember its rule to **regenerate at slide size** (bigger fonts, ~14–18 pt; don't shrink a paper figure onto a slide).

## Reference files
- `references/verification.md` — **read this before you type `marp`.** Why you don't render, the one-process rule + `ps`/`pkill` incantations, and the runnable ~0.1 s checks (slide count/titles, figure paths, div balance, layout lint, undefined helper classes) that replace rendering.
- `references/style_block.md` — the canonical gaia `style:` block to paste into a new deck.
- `references/build_sh.md` — the `build.sh` template + the `marp` conda env setup.
- `references/snippets.md` — copy-paste slide patterns (title triptych, two-col text+figure, pullquote, `.dim` progressive-reveal build, quoted-remarks list, speaker notes, cut candidates, video, citation, references slide).
- `references/uzh_house_style.md` + `references/uzh_frontmatter_{corporate,light,contrast}.yml` — UZH corporate design: the verified palette and typeface, what's CD-specified vs. invented, known warts, and three drop-in front matters.
- `references/positioning.md` — how to place things precisely: the fixed 1280×720 pixel canvas, absolute-`<div>` placement, arrows/labels glued to a figure, full-bleed figure + floating text, background-image syntax, corner-by-alt-text, caption-over-split-bg, panel grids. The "how to place" companion to the gotchas file.
- `references/marp_layout_gotchas.md` — rendering quirks & asset prep: the `--html` flag as root cause, the blank-lines-inside-divs rule, `![h:..vh]` ignored (use px), white letterbox bands on height-sized landscape figures, the ~395px footer ceiling, gaia's blockquote quote glyphs, `<style scoped>` scoping, editing slides by index, `**bold**` in inline divs, EXIF baking, autocrop, `pdftoppm`/PIL asset prep, and build/shell traps. The "what breaks" companion to `positioning.md`.
