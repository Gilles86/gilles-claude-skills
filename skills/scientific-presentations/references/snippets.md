# Slide pattern snippets

Copy-paste patterns for the recurring slide types. All assume the canonical style block (`style_block.md`) is present. Slides are separated by `---`.

## Title slide (triptych)

```markdown
<!-- _footer: '' -->
<!-- _paginate: false -->

## My talk title

<div class="center">

*A one-line italic subtitle / question*

</div>

<div class="two-col" style="margin: 24px 0; align-items: center;">
<div class="col center vcenter">

![height:280px](figures/teaser_left.png)

</div>
<div class="col center vcenter">

![height:280px](figures/teaser_mid.png)

</div>
<div class="col center vcenter">

![height:280px](figures/teaser_right.png)

</div>
</div>

<div class="center text-small">

Gilles de Hollander · ZNE, University of Zurich · Venue 2026

</div>
```

## Two-column: text + figure (the workhorse)

```markdown
## Slide title

<div class="two-col two-col--50">
<div class="col vcenter">

<div class="text-mediumsmall">

- Terse bullet one
- Terse bullet two

</div>

</div>
<div class="col center vcenter">

![width:520px](figures/result.png)

<span class="text-tiny">Author et al. (2026). *Venue* vol: pp.</span>

</div>
</div>
```

Swap `two-col--50` for `two-col--30-70` (text narrow, figure wide) or `two-col--70-30` (figure-led) as needed. For a figure-only slide, drop the text column and use a single centered image.

## Figure-only slide with a one-line caption

```markdown
## Slide title

<div class="center">

![height:580px](figures/big_result.png)

</div>

<div class="text-small center" style="margin-top:0.2em;">

One short caption line — the takeaway, not a description.

</div>
```

## Bullet-only slide (no figure): narrow measure + vertical centring

**A text-only slide gets `.measure` on the text box and `.slide-vcenter` around it.** Both,
always — this is Gilles's default and he has asked for it twice.

```markdown
## Where I stand

<div class="slide-vcenter">

<div class="text-medium measure">

- I was late to this. I thought LLMs were overhyped
- The **agentic** part is what changed my mind

</div>

</div>
```

Why each half matters:

- **`.measure` (max-width 820px).** Bullets running the full 1140px content width give
  ~75-90 characters per line — well past the ~55-75 that reads comfortably, and the eye
  loses the line on the return sweep. 820px lands around 55-60. The text stays
  **left-aligned**; you are narrowing the box, not centring the text.
- **`.slide-vcenter`.** Without it a short list sits jammed under the title with a large
  dead area beneath, which reads as an unfinished slide.

Slides *with* a figure or `two-col` do not need `.measure` — the column already constrains
the measure. Applying it there just makes the column narrower for no reason.

## Evidence left, verdict right (Gilles's default for a list + conclusion)

**When a slide is "several bullets, then a conclusion", put the bullets in a left column and
the conclusion in a narrow right column — not as a centred line underneath.** This is the
house default; reach for it whenever a list needs a payoff line.

Why it beats a line underneath: the conclusion reads as a *verdict on* the list rather than
as a fifth bullet, it stops the slide bottom-loading into the footer, and the eye lands on it
instead of running past it.

```markdown
## Things I only had to say once

<div class="two-col two-col--70-30" style="align-items:center; height:400px;">
<div class="col vcenter">

<div class="text-small">

- *"Do not run anything heavy on the login node"* — after I OOM-killed one
- *"Keep `--time` tight"* — a lax walltime delays your own job

</div>

</div>
<div class="col vcenter">

<div class="text-medium center">

188 memory files, across 19 projects.

<div style="margin-top:0.7em;">

**None of them written twice.**

</div>

</div>

</div>
</div>
```

Notes:
- `two-col--70-30` is the usual split; the verdict wants to be short enough to live in ~340px.
- Set a `height` on the row so the two columns centre against a fixed box (see the build-slide
  section in `marp_layout_gotchas.md` — without it, columns re-centre as content changes).
- Keep the verdict to one or two short lines. If it needs three, it is an argument, not a
  verdict, and belongs in the bullets.

## Pullquote / punchline slide (no figure)

```markdown
<div class="slide-vcenter text-medium center">

<span class="pullquote">Perception shapes decision-making.</span>

</div>
```

## Progressive reveal (a "build"): duplicate the slide, `.dim` the earlier items

MARP has no animation you want. The reveal is **N near-identical slides**; on each one the
already-seen items sit in a `<div class="dim">` and only the new block is at full contrast.
Clicking through reads as an animation.

**Builds cost no talk time** — you are still saying the same sentences — so use them
freely. Anywhere a list would otherwise land as a wall, split it into two or three.

```markdown
## Where my time actually went

<div class="text-mediumsmall" style="margin-top:0.4em;">

<div class="dim">

- Programming (fine, that one is fair enough)
- Cleaning up data

</div>

- Setting up Python environments **again**
- Figuring out why the GPU is suddenly not being used

</div>

<!-- BUILD 2 of 3. Let the repetition land. Do not explain the joke. -->
```

Notes:
- `.dim` is in the canonical style block (`#90a4ae`). Keep the dimmed items **byte-identical**
  across builds so nothing shifts vertically between clicks.
- Number the builds in the speaker note (`BUILD 2 of 3`) — otherwise a later edit desynchronises them.
- **The special case where the crowding is the point:** a list that keeps growing until it
  is absurd. Step the text class *down* each build (`.text-mediumsmall` → `.text-small`) and
  let the last slide be genuinely cramped. That is the joke; don't fix it.

## A list of quoted remarks (do **not** use `>`)

gaia's blockquote adds decorative quote glyphs of its own, which double up with your
literal quotes and float the closing one far right. Use typographic quotes in a plain div:

```markdown
## Things people have said to me over the years

<div class="slide-vcenter">

<div class="text-medium" style="line-height:1.5;">

“Why run it on the cluster? Just leave your laptop on overnight”

“You do not need computational graph libraries, you can do that in Matlab”

“This is how we have always done it”

</div>

</div>
```

## Speaker notes

Plain HTML comments on the slide — MARP's presenter view picks them up. One per slide,
written as what Gilles *says*, not a summary of what is on the slide.

```markdown
<!-- I want to be fair here first, because these were reasonable things to say. Learning a new stack cost you three weeks you did not have. -->
```

**Avoid `--` inside a comment** — a double hyphen can terminate the comment early and dump
the rest of your note onto the slide. Write it out, or use an em dash character, never `--`.

## Cut candidates: mark, don't delete

A talk always needs shortening late. Mark the removable slides in the source instead of
deleting them, so shortening is one delete and nothing is lost:

```markdown
<!-- CUT CANDIDATE (outline: "cut one of the two question-first examples,      -->
<!-- keep the numerosity one, it is closer to what most of the room does").    -->

## Start from the question: working memory noise
```

Keep the reasoning inside the marker, and list them in the deck's `README.md` as a cut plan,
ordered: cut in advance / cut live if running long / **do not cut**.

## Video slide (HTML output only)

```markdown
## Slide title

<div class="center">
<video controls width="900" autoplay loop style="max-height: 560px;">
  <source src="figures/clip.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>
</div>

<div class="text-tiny center" style="margin-top: 0.2em;">

Source / credit.

</div>
```

## Section divider (comment in source — not a rendered slide)

```markdown
<!-- ============================================================== -->
<!-- §N — SECTION NAME                                               -->
<!-- ============================================================== -->
```

## References slide (multi-column, tiny)

```markdown
## References

<div class="text-tiny">

**Framework**
- Author (Year). Title. *Venue* vol: pp.

**Domain**
- Author (Year). Title. *Venue* vol: pp.

**Own work**
- de Hollander et al. (Year). Title. *Venue*.

</div>
```

## Closing slide

```markdown
<!-- _footer: '' -->
<!-- _paginate: false -->

# Thank you

Questions?

<div class="text-small" style="margin-top: 1em;">

Collaborators · funding · acknowledgements

</div>
```

## Inline citation (anywhere)

```markdown
<span class="text-tiny">Wei & Stocker (2017). *Nat Neurosci* 20: 1314–1321.</span>
```
