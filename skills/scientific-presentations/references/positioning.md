# Positioning elements precisely (gaia, enableHtml)

The reflex when something won't sit where you want is to fight the markdown flow. Don't. MARP gives you a **fixed pixel canvas** and full CSS — the fast path is to drop one absolutely-positioned `<div>` and type coordinates while watching the live preview. This file is the positioning *toolkit* (how to place things); its sibling **`marp_layout_gotchas.md`** is the *troubleshooting* list (what silently fails and why). Read both — and when a position/size doesn't take, the gotchas file is where the answer usually is.

**Critical constraint that shapes everything here:** `<!-- _class: foo -->` does **not** survive static export — MARP emits it as `data-class="foo"`, so a `section.foo {}` rule never matches in the exported HTML/PDF (see `marp_layout_gotchas.md`). So none of the patterns below pin layout to a section class. To override section CSS for one slide, use `<style scoped>…</style>` (confirmed working); for reusable layout, put the class on a `<div>` (div/img classes survive). Verify any tricky slide by rendering its PNG (`./build.sh png`) and *looking* — don't trust that the markup did what you meant.

## The one fact that makes positioning tractable: the slide is a fixed pixel canvas

The slide **is** the `<section>` element, rendered at a literal fixed size and then CSS-scaled to whatever it's displayed/exported at. So a coordinate you type is stable across preview, PDF, and projector.

| Aspect ratio | `<section>` size | Center | Horizontal thirds |
|---|---|---|---|
| **16:9 (gaia default)** | **1280 × 720 px** | `640px, 360px` | `427px`, `853px` |
| 4:3 | 960 × 720 px | `480px, 360px` | `320px`, `640px` |

You author in this fixed space. `top: 360px; left: 640px` is the true center of a 16:9 slide, always.

**The padding gotcha that wastes the most time:** gaia sets `section { padding: 70px }`, and the house-style block adds `padding-bottom: 90px` (to reserve footer room). Absolutely-positioned children resolve against the section's *padding box*, so `top:0; left:0` lands at `(70, 70)` — the inner corner — and `bottom:0` floats ~90px above the true bottom. Two fixes:
- Keep the padding and offset your coordinates (usable inner box is `70px → 1210px` wide, `70px → 630px` tall), **or**
- Zero the padding for that one slide with a scoped style, so coordinates equal true slide pixels:
  ```markdown
  <style scoped>section { padding: 0 !important; }</style>
  ```
  Cleaner for full-bleed figure slides — prefer this. (Do **not** reach for `<!-- _class: bleed -->`; a section `_class` won't match a `section.bleed{}` rule in static export — see the critical constraint above.)

Other gotchas: **units are mandatory** (`760px`, never `760`); raw HTML only renders with `enableHtml` on (it is, in the marp env / VS Code); `section::after` is reserved by MARP for the page number, so use `::before` for your own pseudo-element overlays.

## 1. Place a figure (or anything) at an exact spot

The workhorse. Zero the padding with a scoped style, then one absolutely-positioned div, explicit `width`, coordinates from the table above.

```markdown
<style scoped>section { padding: 0 !important; }</style>

<div style="position:absolute; top:120px; left:740px; width:460px;">

![width:460px](figures/prf_fit.png)

<span class="text-tiny">Figure 1. PRF fit, V1.</span>

</div>
```

With padding zeroed, `top/left` are true slide pixels (drop the scoped style and add 70 to each if you'd rather keep the footer margin). Always set an explicit `width` so text wrapping is predictable. Blank lines around markdown *inside* a `<div>` are required for MARP to parse the markdown (image, `![...]`, spans) — without them it leaks as literal text.

## 2. Glue a label or arrow onto a figure (relative wrapper)

To annotate a figure so the label *moves with it*, wrap the image in a `position:relative` box and pin children in **percentages** — now the coordinates are relative to the figure, not the slide.

```markdown
<div style="position:relative; width:600px; margin:auto;">

![width:600px](figures/brain_map.png)

<span style="position:absolute; top:42%; left:55%; color:#e8590c; font-weight:bold; font-size:22px;">V1</span>
<img src="figures/arrow.svg" style="position:absolute; top:30%; left:20%; width:80px;">

</div>
```

This is the right pattern for arrows, ROI labels, "you are here" markers — anything that must stay registered to image content.

## 3. Full-bleed background figure with a floating text box

Big figure filling the slide, a legible caption/title floated over it. Backgrounds always render behind content, so a floated box naturally sits on top.

```markdown
<style scoped>section { padding: 0 !important; }</style>

![bg cover](figures/full_brain_render.png)

<div style="position:absolute; top:80px; right:80px; width:440px; background:rgba(0,0,0,.6); color:#fff; padding:24px 28px; border-radius:8px; z-index:3;">

## Population receptive fields

<span class="text-small">Eccentricity increases posterior→anterior along the calcarine.</span>

</div>
```

If the background figure is busy, dim it so text reads: `![bg cover brightness:.5 blur:3px](...)`.

## 4. Background image syntax (the other main tool — pure Marpit)

The `![bg ...]` keyword goes in the image's alt text. Ideal for full-bleed and split layouts; no HTML needed.

```markdown
![bg](fig.png)              # fills slide (default = cover)
![bg contain](fig.png)      # fit whole figure, no crop  (alias: bg fit)
![bg cover](fig.png)        # fill, may crop
![bg 150%](fig.png)         # explicit scale

![bg left](fig.png)         # figure = left half, content flows right
![bg right:40%](fig.png)    # custom split width — the "big figure + bullets" slide

![bg](a.png)                # multiple bgs tile horizontally...
![bg](b.png)
![bg vertical](a.png)       # ...or stack vertically
![bg](b.png)
```

Filters (space-separated, combinable): `blur:6px`, `brightness:.5`, `opacity:.4`, `contrast`, `grayscale`, `saturate`, `sepia`, `hue-rotate`, `invert`, `drop-shadow`.

For pixel-precise background placement, use the scoped directives instead (full CSS `background-*` vocabulary, one slide):

```markdown
<!-- _backgroundImage: url('figures/panel.png') -->
<!-- _backgroundSize: 600px -->
<!-- _backgroundPosition: 900px 100px -->
<!-- _backgroundRepeat: no-repeat -->
```

## 5. Corner placement by alt text (define once, reuse everywhere)

Style images by keywords in their alt text using attribute selectors. The selectors live in the style block; you just write the keyword. Good for logos, source tags, small annotations.

```markdown
![top-right w:120](figures/lab_logo.png)
![bottom-left w:500](figures/inset.png)
```

The selectors (`img[alt~="top-right"]` etc.) are in `style_block.md` — see §"Positioning helpers". This pattern is from Miriam Müller's MARP cheatsheet (credited below).

## 6. Caption over a split background (maintainer pattern)

On a `![bg left]` slide, raw HTML is trapped in the shrunken content column, so to caption *over* the background use `section::before` with a scoped style:

```markdown
![bg left](figures/cortex.png)

<style scoped>
section::before {
  content: 'Spinoza Centre, 7T';
  position: absolute; bottom: 30px; left: 30px;
  font-size: 18px; color: #fff;
  background: rgb(0 0 0 / .7); border-radius: 4px; padding: 4px 10px;
}
</style>

## Slide title and bullets (right side)
```

`<style scoped>` confines the rule to this one slide. For overlays on *inline* (non-background) figures, prefer the relative-wrapper pattern in §2 instead — it's more flexible.

## 7. Multi-panel grid

For N figure panels in a clean grid, a CSS-grid class beats nested `.two-col`. The classes (`.panel-grid-2`, `.panel-grid-3`) are already in the style block — they go on the **wrapper `<div>`**, not the section (a div class survives static export; a section `_class` would not):

```markdown
<div class="panel-grid-2">

![](figures/a.png)
![](figures/b.png)

</div>
```

## Quick decision guide

| Goal | Technique |
|---|---|
| Big figure filling the slide | `![bg cover/contain]` (§4) |
| Figure one side, bullets other | `![bg left:55%]` + content (§4) — or `.two-col` from `snippets.md` |
| Figure at an exact pixel spot | absolute `<div>` + scoped `padding:0` (§1) |
| Label / arrow glued to a figure | `position:relative` wrapper, `%` children (§2) |
| Text legible over a busy figure | `![bg brightness:.5 blur:3px]` + floated box w/ `z-index` (§3) |
| Caption over a split background | `section::before` + `<style scoped>` (§6) |
| Logo / source tag in a corner | alt-text class `![top-right ...]` (§5) |
| N-panel figure grid | CSS-grid `_class` (§7) |

## Tooling

There is **no drag-to-position** — MARP is markdown/CSS-first by design. The practical substitute is the **Marp for VS Code** split preview: type a coordinate, watch it move, repeat. `./build.sh watch` gives the same live loop in a browser. Mental ruler: center `640,360`; with gaia padding the usable inner box is `70→1210 × 70→650`.

## Sources & credits

- **Official Marpit docs** — background-image syntax, local/scoped directives, the theme-CSS slide-size model. The canonical spec; not "borrowed" so much as the language itself. <https://marpit.marp.app/image-syntax>, <https://marpit.marp.app/directives>, <https://marpit.marp.app/theme-css>
- **gaia theme source** — the `padding: 70px` and `.lead`/`.invert` classes that drive the coordinate offset. <https://github.com/marp-team/marp-core/blob/main/themes/gaia.scss>
- **Miriam Müller**, *Marp Advanced Image Positioning* / Marp Cheatsheet — the `img[alt~="keyword"]` alt-text attribute-selector pattern in §5 and the style block. <https://miriam-mueller.com/marp-advanced-image-positioning/>
- **Marp maintainer (`@yhatt`)**, GitHub Discussion #606 — the `section::before` caption-over-split-background pattern in §6. <https://github.com/orgs/marp-team/discussions/606>
