# MARP rendering quirks & asset prep

Hard-won lessons from real decks. For **coordinate positioning** (absolute pixel placement, `.bleed`, background images, multi-panel grids) see **`positioning.md`** — that's the authoritative positioning reference. This file covers the *rendering quirks* (what survives the markdown→HTML pass) and *asset prep* that bite regardless of layout approach.

**Do not verify by rendering.** Gilles has `./build.sh watch` open in a browser and he is the visual verifier; a marp process of yours steals his Chrome and stalls his preview. Everything in this file is either mechanically checkable (see **`verification.md`** for the lint that catches most of it in ~0.1 s) or something you tell him to look at. Also don't trust a truncated HTML grep — a real `class=` can sit far down a long `<section>` tag.

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

## White letterbox bands: size landscape figures by **width**, not height

The house style sets `section img { background-color: #fff }` so transparent figures
composite on white instead of picking up the slide tint. Combine that with
**height**-based sizing on a **landscape** figure inside a **narrower column** and
`.col img { object-fit: contain }` letterboxes it — and those letterbox bands are *white*,
so on a cream/off-white ground they show as two bright slabs flanking the figure. It reads
as a rendering bug.

- **Landscape figure in a column → `![width:520px](…)`.** Width-based sizing is the default
  for two-col figures; it can't letterbox horizontally.
- **Height-based sizing is for portrait figures**, and for full-width figures where the
  column *is* the slide.
- Same mechanism on an off-white deck ground (`uzh_light`): the forced-white image
  background shows as a faint box behind every figure. See `uzh_house_style.md`.

## Build slides: use fragments, NOT duplicated slides

**Default to Marp's fragmented lists. Do not hand-duplicate a slide per reveal step.**

Change the bullet marker from `-` to `*` (or `1.` to `1)` for ordered lists) and Marp emits
`data-marpit-fragment="N"` on each item; the bespoke HTML template reveals them one click at
a time.

**The decisive detail:** inactive fragments are hidden with
`[data-bespoke-marp-fragment=inactive] { visibility: hidden }` — **`visibility`, not
`display`**. Every item therefore occupies its final position from the very first step, so
**nothing reflows as the list grows**. Duplicated slides do the opposite: each copy is laid
out from scratch, so items shift between clicks and any figure beside them drifts. That
jumping is the single most common ugly-build complaint, and fragments eliminate it by
construction.

Fragments also work on **arbitrary elements**, not just list items — write the attribute by
hand and bespoke picks it up (verified; survives the `--html` pass):

```html
<div data-marpit-fragment="5">

...a punchline, a figure, anything...

</div>
```

That means a whole build — bullets appearing one by one, then a closing line and an image
together — fits on **one** slide.

Limits, and when you still need duplicate slides:

- **HTML only.** PDF/PPTX render every fragment visible. A `?pdf` preview therefore always
  shows the *final* state — you can verify the finished layout but never the intermediate
  steps. Only the browser has fragments.
- **Fragments reveal; they do not restyle.** They cannot grey out earlier items or step the
  font down as a list crowds. A build that *transforms* earlier content (dimming, resizing)
  still needs one slide per step.

### If you must duplicate slides: pin the row height

For a genuine multi-slide build with a figure alongside a growing list, `align-items: center`
re-centres **every** column against the row's height. As the list grows the row grows, the
figure re-centres in a taller box, and it visibly drifts down the screen between clicks.

Pin the row and top-anchor the growing column:

```html
<div class="two-col two-col--70-30" style="align-items: stretch; height: 436px;">
<div class="col">            <!-- list: top-anchored, grows downward -->
...
<div class="col center vcenter">   <!-- figure: centred in a fixed-height box -->
```

Size the height from the *tallest* step. Apply it to every step in the sequence — a build
whose steps disagree by even a few pixels reads as a jitter.

## Code blocks: marp auto-scales code to its container, so narrowing `<pre>` shrinks the *font*

A `<pre>` spanning the full slide with a short longest-line looks wrong — a wide dark box
with the text filling half of it. The instinct is to make the box hug its content. **Do not
use `width: fit-content`.**

Marp Core auto-fits code blocks (the content is wrapped and scaled to the container width),
so container width and type size are coupled: **narrower container = smaller type**, not just
a smaller box. `width: fit-content` collapses the container to the intrinsic width and the
code renders at roughly **5px** — technically "hugging its content", completely unreadable.

Use a fixed `max-width` instead, and centre it:

```css
  /* Narrower, centred code blocks. NOTE: marp auto-scales code to the
     container, so a much smaller max-width shrinks the type — 980px is
     about the floor before it gets hard to read from the back. */
  section pre {
    max-width: 980px !important;
    margin-left: auto !important;
    margin-right: auto !important;
  }
```

**~980px is about the floor** on the 1280px canvas before the type gets too small to read from
the back of a room. Keep the comment in the style block — without it this reads like an
arbitrary magic number and someone "tidies" it to `fit-content` again.

Corollary: if a code block still feels too wide to read comfortably, the fix is **shorter
lines in the excerpt**, not a narrower container. Re-wrap or trim the code before you touch
the CSS.

## Footer collisions: ~395px is the ceiling for a captioned full-width figure

The style block reserves 90px at the bottom for footer + page number. A full-width figure
**plus a caption line** below it needs the image at or under **~395px** of height, or the
caption lands on the footer. Without a caption you have more room (a bare centered figure
takes ~580px). The lint in `verification.md` flags `height:>395px` on any slide that also
carries a `text-small`/`text-tiny` caption div.

## gaia blockquotes add their own quote glyphs — don't use `>` for quoted remarks

`> "Why run it on the cluster?"` renders with gaia's big decorative quote marks *plus*
your literal `"` → **doubled quotes**, and gaia's closing glyph floats far out to the
right, unattached to anything. For a slide that is a *list* of quoted remarks (a very
useful pattern — see `snippets.md`), drop the blockquote entirely: use typographic quotes
inside a styled `<div>`.

## `<style scoped>` works, and it does not leak

Verified in exported HTML: marp stamps a unique `data-marpit-scope-XXXXXXXX` attribute on
that one `<section>` and rewrites the rule's selector to match only it. So
`<style scoped>section { padding-top: 28px !important; }</style>` on a title slide changes
that slide and nothing else. It is the right tool for a per-slide padding override — more
targeted than a `_class` and a global rule.

## Identical slides: an exact-match replace hits both

Title slides and closing slides very often share identical markup (`<!-- _footer: '' -->`,
`<!-- _paginate: false -->`, a centered block). A whole-file
`text.replace(old, new)` then silently edits **both**, and you find out at the podium.
Use `text.replace(old, new, 1)`, or — better — address slides by index.

## Editing slides programmatically: split on `\n---\n`, edit by index

Far more reliable than regex over the whole file. Split off the front matter, split the
body into a list of slides, mutate the list, re-join.

```python
from pathlib import Path

p    = Path("my_talk.md")
text = p.read_text(encoding="utf-8")
end  = text.index("\n---\n", 3) + len("\n---\n")   # end of the YAML front matter
fm, body = text[:end], text[end:]
slides   = body.split("\n---\n")                   # slide 1 == slides[0]

slides[7]  = slides[7].replace("![height:480px]", "![height:395px]")  # rewrite slide 8
slides.insert(12, NEW_SLIDE)                                          # insert before 13
slides.append(slides.pop(3))                                          # move slide 4 to the end

p.write_text(fm + "\n---\n".join(slides), encoding="utf-8")
```

Two rules: index arithmetic is 0-based while everyone *talks* about slides 1-based, so
print the titles (`verification.md` §1) before and after; and never `strip()` a slide — the
leading/trailing newlines are what keep the `---` separators well-formed.

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
- **Transparent figures pick up the gaia tint.** The house style sets `section img { background:#fff }` so they composite on white; exempt logos with `img.logo { background:transparent !important }` (a white box behind a logo looks unprofessional). Note this is also what makes height-sized landscape figures letterbox in white — see above.
- **PDF figure → PNG:** `pdftoppm -png -r 200 in.pdf out` (poppler; already installed). 200 dpi is the right default for a slide — 150 is visibly soft on a projector, 300 just bloats the deck. Output lands at `out-1.png`.
- **`.webp` → `.png`** (journal sites serve webp; marp handles it, but PIL edits don't round-trip well):
  ```python
  from PIL import Image
  Image.open("fig.webp").convert("RGB").save("fig.png")
  ```
- **Crop a published multi-panel figure down to the panels that match yours.** For an
  original-vs-reproduction comparison, showing their 6-panel figure next to your 2-panel
  replication is not like-for-like and the audience spends the slide hunting for the
  correspondence. Crop theirs to the same panels:
  ```python
  from PIL import Image
  im = Image.open("published.png")
  w, h = im.size
  im.crop((0, 0, w // 3, h // 2)).save("published_ab.png")   # top-left 2 panels
  ```
  Print `im.size` first and iterate on the fractions; it takes two or three tries and no render.

## Build / shell traps

- **Never start a marp process while the user's `--watch --server` is running**, and never
  run two at once — they contend for the same headless Chrome and 1-second builds become
  5-minute hangs. Full rules, timings and the `ps`/`pkill` incantations: **`verification.md`**.
- `marp --server`/any `marp` call needs **node on PATH**; launch via the same export `build.sh` uses (`export PATH="$HOME/mambaforge/envs/marp/bin:$PATH"`) or it dies with `env: node: No such file or directory`.
- **Live preview:** `./build.sh watch` serves `http://localhost:8080/<deck>.md` and auto-reloads on save — far better than rebuilding each edit. The static `<deck>.html` only updates on `./build.sh html`.
- In non-interactive / background Bash, `cp`/`mv` may be aliased to `-i` and **hang on an overwrite prompt**. Use `/bin/cp -f` / `/bin/mv -f` when overwriting generated assets.
- Chaining `cat <<EOF … marp … python` in one Bash call can get auto-backgrounded and silently drop outputs; run the `marp` render as its own foreground command, then inspect.
