# MARP rendering quirks & asset prep

Hard-won lessons from real decks. For **coordinate positioning** (absolute pixel placement, `.bleed`, background images, multi-panel grids) see **`positioning.md`** — that's the authoritative positioning reference. This file covers the *rendering quirks* (what survives the markdown→HTML pass) and *asset prep* that bite regardless of layout approach.

Always verify by rendering a PNG of the specific slide (`./build.sh png` → `slide.0NN.png`) and *looking* at it. Don't trust that markup did what you intended — and don't trust a truncated HTML grep either (a real `class=` can sit far down a long `<section>` tag).

## THE root cause of "my layout vanished": the `--html` flag

Easily the highest-value lesson. **Pass `--html` to every marp-cli invocation** (it's in the house `build.sh`). Without it, marp-cli sanitizes raw HTML and **silently strips inline `style` and `id` from your tags**. What survives the strip is exactly what makes the bug hard to see: `class` survives, and MARP's own `![w:..]`/`![h:..]` image sizing survives — so *some* things still work while every `<div style="display:flex…">`, every `position:absolute` box, and every `<video width=…>` quietly loses its attributes and collapses to default flow.

Verified with `--html` ON: `<div style="color:red">` → keeps style; `<video width="500" style="height:300px">` → keeps **both**. Verified with it OFF: same tags render as bare `<div>` / `<video>`. So earlier "blank lines strip attributes" and "video drops style" diagnoses were both wrong — they were *all* the missing flag.

Gotchas about the flag:
- The front-matter `html: true` directive does **not** work; it must be the CLI flag (or a marp config file).
- **VS Code's Marp preview enables HTML by default**, so a layout can look perfect in preview and break only in the `build.sh` export. Always sanity-check the exported HTML/PDF, not just preview.

## `vh` means different things in preview vs export — prefer px

The slide is a fixed **1280×720** canvas. But CSS `vh`/`vw` resolve against the **rendering viewport**:
- in **PNG/PDF export**, the viewport *is* the 720px slide, so `height:80vh` ≈ 576px — fits.
- in the **served / live-preview HTML** (`build.sh watch`, VS Code), the viewport is the **browser window**, so `height:80vh` can be far taller than the slide → content overflows and **clips at the bottom**.

This bit hard: a title slide wrapped in `height:86vh` looked fine in the PNG export but was cropped in the browser. **Author heights/positions in `px` against the 1280×720 canvas** (or use the `.bleed` + absolute-px approach in `positioning.md`). Reserve `vh` for throwaway checks, never final layout.

## Image sizing: px, not viewport units

- MARP's `![width:NNNpx](...)` / `![height:NNNpx](...)` accepts **px** (and `%`). **`vh`/`vw` are not parsed as a size — they fall through to the image's `alt` text** and the image renders at natural pixel size (often enormous). Verified: `![height:50vh](x)` → `<img alt="height:50vh">` (no sizing); `![height:300px](y)` → `<img style="height:300px">`. Always size images in **px**.

## Markdown inside a `<div>` needs blank lines (a *content*-parsing rule, not an attribute one)

- **Put a blank line after `<div ...>` and before `</div>`** if you want Markdown *inside* it parsed (image `![]`, `*italics*`, `##`, `**bold**`). Without the blank line the inner Markdown leaks as literal text. (This is a markdown-it HTML-block rule; it does **not** affect whether the div's own attributes survive — that's the `--html` flag above.)
- Corollary: **`**bold**` does not render inside a single-line inline `<div>`** (`<div class="text-medium">**~20 W**</div>` shows literal asterisks). Use `<strong>~20 W</strong>`, or break it onto its own line with blank lines around it.

## Video sizing & centering

- With `--html` on, `<video>` keeps `style` *and* `width=`/`height=`. Size it however; `height="470"` (px) is a safe way to fit a clip under a title without clipping.
- **Center video** with `.center` on the wrapper (a `<video>` is inline-level, so `text-align:center` centers it) — the simplest reliable horizontal centering, same mechanism that centers `![]` images.
- Build with `--allow-local-files` or video/images won't embed; videos only play in **HTML** output (keep a static fallback image for PDF).

## Positioning, briefly (full details in positioning.md)

The earlier draft of this file claimed `_class:` only emits `data-class` and that absolute positioning is unreliable. **Both were wrong.** Verified facts:
- **`_class: foo` emits a real `class="foo"`** on the `<section>` (alongside a `data-class` mirror), so `section.foo { … }` rules *do* match in marp-cli static export.
- **Absolute positioning is reliable** when (a) the section is `position:relative` and (b) you account for gaia's `padding:70px` — both handled by the `.bleed` class (`section.bleed{ padding:0; position:relative }`). On a `.bleed` slide, `top/left` are true 1280×720 slide pixels. This is the house pattern — see `positioning.md`.
- A flex-column wrapper (`display:flex; flex-direction:column; justify-content:space-between; height:86vh`) is a fine alternative for simple "title / body / footer-row" slides and avoids coordinates entirely. (Earlier confusion about pinning a logo to the bottom was the missing `position:relative` + gaia padding, *not* anything broken about `_class` or absolute.)

## Asset prep (do this in figures/, before placing)

- **EXIF-rotated phone photos** display sideways in some renderers. Bake orientation in:
  ```python
  from PIL import Image, ImageOps
  ImageOps.exif_transpose(Image.open(f)).save(f, quality=90)
  ```
- **Equal-height images look unequal** when one has internal whitespace / transparent margins (a nilearn/matplotlib export with a wide border). Autocrop to the content box:
  ```python
  from PIL import Image
  im = Image.open(f).convert("RGBA"); im.crop(im.split()[3].getbbox()).save(f)
  ```
- **Transparent figures pick up the gaia tint.** The house style sets `section img { background:#fff }` so they composite on white; exempt logos with `img.logo { background:transparent !important }` (a white box behind a logo looks unprofessional).

## Build / shell traps

- `marp --server`/any `marp` call needs **node on PATH**; launch via the same export `build.sh` uses (`export PATH="$HOME/mambaforge/envs/marp/bin:$PATH"`) or it dies with `env: node: No such file or directory`.
- **Live preview:** `./build.sh watch` serves `http://localhost:8080/<deck>.md` and auto-reloads on save — far better than rebuilding each edit. The static `<deck>.html` only updates on `./build.sh html`.
- In non-interactive / background Bash, `cp`/`mv` may be aliased to `-i` and **hang on an overwrite prompt**. Use `/bin/cp -f` / `/bin/mv -f` when overwriting generated assets.
- Chaining `cat <<EOF … marp … python` in one Bash call can get auto-backgrounded and silently drop outputs; run the `marp` render as its own foreground command, then inspect.
