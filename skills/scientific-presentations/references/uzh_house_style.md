# UZH corporate design for MARP decks

For talks given as UZH (lab meeting, department seminar, institute colloquium). Three
ready-made front matters ship with this skill — paste one over a deck's front matter and
the body needs no edits:

| file | look |
|------|------|
| `uzh_frontmatter_corporate.yml` | white ground, UZH Blue headings, a thin blue rule under every slide title. **The default — pick this one.** |
| `uzh_frontmatter_light.yml` | off-white ground, neutral dark-grey titles at weight 300, blue held back to accents. Reads like a well-set seminar deck rather than an institutional one. |
| `uzh_frontmatter_contrast.yml` | pure white, pure black text, a full-bleed blue bar across the top of every content slide, blue pullquote slides. For a bright room / washed-out projector. |

All three define every helper class in `style_block.md` plus `.dim`, `.chip`, `.srcref`,
so any snippet from `snippets.md` works unchanged. Change `footer:` and go.

## Colours — VERIFIED, do not "fix" these

Checked in an earlier session against the official UZH colour sheet
(`uzh-corporate-colors-cmyk.pdf`, fetched and text-extracted) and
<https://www.cd.uzh.ch/en/elements.html>. Several of these were **wrong in an earlier
guess and have been corrected**; the values below are the sheet's, so if one looks off to
you, it is your memory that is off.

| | hex |
|---|---|
| **UZH Blue** | `#0028A5` (Pantone 286 C) |
| UZH Cyan | `#4AC9E3` |
| UZH Apple | `#A5D233` *(not `#A4D233`)* |
| UZH Gold | `#FFC845` |
| UZH Orange | `#FC4C02` *(not `#DC6027`)* |
| UZH Berry | `#BF0D3E` |

Blue tints, V1→V5: `#BACBFF` `#7596FF` `#3062FF` `#001E7C` `#001452`

**The greys are neutral, not blue-tinted** (an earlier guess used a blue-tinted
`#A3ADB7` — wrong):

- Grey V1→V5: `#C2C2C2` `#A3A3A3` `#666666` `#4D4D4D` `#333333`
- Light Grey V1→V5: `#FAFAFA` `#EFEFEF` `#E7E7E7` `#E0E0E0` `#D7D7D7`

## Typeface — VERIFIED

The UZH corporate typeface is **Source Sans Pro** (per cd.uzh.ch: "available as a Google
Webfont free of charge"). **Not Theinhardt** — TheSans is the logo/signage face and
Palatino is used on graduation certificates; an earlier guess named Theinhardt as the
corporate face and that was wrong.

Offline-safe stack, no `@import`, no web-font download (renders work with no network):

```css
font-family: "Source Sans Pro", "Source Sans 3", "Inter",
             "Roboto", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
```

To get the real face locally: `brew install --cask font-source-sans-3`. Without it the
stack falls back to Roboto/Helvetica, which is close enough that layout does not shift.

Note gaia itself `@import`s Lato and Roboto Mono from `fonts.bunny.net`. The variants
override the body font so prose is identical offline; code blocks fall back to the system
monospace. Pin it with `section code { font-family: Menlo, Consolas, monospace !important; }`
if that matters.

## CD-specified vs. invented in the spirit of the CD

Keep this distinction — a future reader must not mistake one for the other.

**CD-specified** (from the official sources above):
- the colour values and their V1–V5 tint ladders
- Source Sans Pro as the corporate typeface

**Design choices invented here, not UZH specification:**
- the thin blue rule under the slide title (`corporate`)
- the full-bleed blue title bar (`contrast`)
- the blue pullquote / section-divider slides (`contrast`)
- all whitespace, rule weights, type sizes, and the code-block colours
- logo placement — none of the variants put the UZH logo on every slide, which a strict
  reading of the CD would probably want. The reference deck carries it on the closing slide only.

The full "Regulations on the Corporate Design of the University of Zurich" PDF has **not**
been read — only the colour sheet and the CD-elements page.

## Known warts

- **`uzh_light`: the forced-white image background shows.** The house style sets
  `section img { background-color:#fff }` so transparent figures composite on white. On
  `uzh_light`'s off-white `#FAFAFA` ground that white box is faintly visible behind every
  figure. Either accept it, or switch that variant's rule to
  `section img { background-color:#FAFAFA }` (and re-check any figure that assumes white).
- **`uzh_contrast` uses `:has()`** for the blue pullquote slides (Chrome 105+; fine in the
  current marp Chrome). On an older renderer those slides fall back to white with blue
  type — nothing breaks.
- **`uzh_contrast`'s blue bar collides with the top-corner image helpers.**
  `img[alt~="top-left"]` / `top-right` place at `top:30px`, i.e. *on* the bar. Use a bottom
  corner, or bump the offset to ~110px.
- **Letter-spacing:** the variants drop gaia's 1.25px to 0.2px. More corporate, and it buys
  ~5% horizontal slack — nothing that fitted before wraps.
- The blue rule in `corporate` costs ~8px of vertical room per slide; the bar in `contrast`
  *gains* ~3px because it eats the top padding.

## Swapping a whole deck's look

The body never changes — only the front matter. To generate variants of a live deck
without touching it, use the splice pattern (split at the end of the front matter, keep the
body byte-identical, assert it): `styles/make_variants.py` in
`presentations/2026/agentic_ai_in_cogneuro/` is the worked version, and the same split is
the basis of every check in `verification.md`.
