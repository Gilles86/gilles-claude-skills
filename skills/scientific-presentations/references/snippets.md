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

## Pullquote / punchline slide (no figure)

```markdown
<div class="slide-vcenter text-medium center">

<span class="pullquote">Perception shapes decision-making.</span>

</div>
```

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
