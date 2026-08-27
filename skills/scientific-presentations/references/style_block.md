# Canonical gaia style block

Paste this front-matter + `style:` block at the top of a new research-talk deck. It encodes: footer/page-number styling, tightened h1/h2/h3 spacing (titles use `##`), the `.two-col` grid with width presets, centering helpers, and the text-size class ladder. This is the refined version from `neuroimaging_encoding_models2026`.

```markdown
---
marp: true
theme: gaia
math: mathjax
paginate: true
footer: My venue · City · 2026
style: |
  /* Reserve room at the bottom so content never slides under footer / page number */
  section {
    padding-bottom: 90px !important;
  }
  /* Footer: smaller, lighter, centered */
  section > footer {
    font-size: 14px !important;
    color: #90a4ae !important;
    left: 0 !important;
    right: 0 !important;
    text-align: center !important;
    padding-bottom: 18px !important;
  }
  /* Page number: smaller, lighter */
  section::after {
    font-size: 14px !important;
    color: #90a4ae !important;
    padding-bottom: 18px !important;
  }
  h1 {
    font-size: 1.5em !important;
    margin-block-start: 0.2em !important;
    margin-block-end: 0.3em !important;
  }
  /* Slide titles use ## (h2) in this deck — tighten them */
  section h2 {
    font-size: 1.0em !important;
    line-height: 1.1 !important;
    margin-block-start: 0 !important;
    margin-block-end: 0.2em !important;
  }
  /* Pull h1/h2 closer to the top so content has more vertical room */
  section > h1:first-child,
  section > h2:first-child {
    margin-top: -0.4em !important;
  }
  section h3, section h4 {
    font-size: 1.0em !important;
    margin-block-start: 0.1em !important;
    margin-block-end: 0.3em !important;
  }
  .two-col {
    display: flex !important;
    gap: 2rem !important;
    align-items: stretch !important;
    width: 100% !important;
  }
  .two-col > .col {
    min-width: 0 !important;
    flex: 1 1 0% !important;
  }
  .two-col--50 > .col         { flex: 1 1 0% !important; }
  .two-col--30-70 > .col:first-child { flex: 3 1 0% !important; }
  .two-col--30-70 > .col:last-child  { flex: 7 1 0% !important; }
  .two-col--70-30 > .col:first-child { flex: 7 1 0% !important; }
  .two-col--70-30 > .col:last-child  { flex: 3 1 0% !important; }
  .col img { max-width: 100%; max-height: 100%; object-fit: contain; }
  /* Composite transparent figures onto white so nothing picks up the slide tint.
     NB: this is exactly why height-sizing a LANDSCAPE figure inside a column shows
     white letterbox bands — size landscape figures by width. See marp_layout_gotchas.md. */
  section img { background-color: #ffffff; }
  img.logo { background: transparent !important; }
  .vcenter {
    display: flex !important; flex-direction: column !important;
    justify-content: center !important;
  }
  .center { text-align: center !important; }
  .fit { font-size: 0.8em; }
  .text-medium     { font-size: 30px !important; line-height: 1.4; }
  .text-mediumsmall { font-size: 27px !important; line-height: 1.3; }
  .text-small      { font-size: 24px !important; line-height: 1.3; }
  .text-twenty     { font-size: 20px !important; line-height: 1.3; }
  .text-tiny       { font-size: 16px !important; line-height: 1.3; }
  .code-small      { font-size: 14px !important; }
  .code-small pre, .code-small code { font-size: 15px !important; line-height: 1.35 !important; }
  /* Narrower, centred code blocks. NOTE: marp auto-scales code to the
     container, so a much smaller max-width shrinks the type — 980px is
     about the floor before it gets hard to read from the back. Do NOT
     use width:fit-content here (collapses the type to ~5px). */
  section pre {
    max-width: 980px !important;
    margin-left: auto !important;
    margin-right: auto !important;
  }
  .pullquote       { font-size: 36px !important; line-height: 1.25; font-style: italic; }
  /* Bullet-only slides: cap the measure. The full slide width is ~75-90
     characters per line at .text-medium, far too wide to read comfortably;
     ~820px lands around 55-60. Text stays LEFT-aligned; only the box narrows. */
  .measure { max-width: 820px !important; }
  /* Dim already-seen items on a build slide so the new block reads as "the reveal".
     See snippets.md § progressive reveal. */
  .dim { color: #90a4ae !important; }
  .dim li::marker { color: #90a4ae !important; }
  /* Small grey chip (timings on section-opener slides) */
  .chip { font-size: 18px !important; color: #78909c !important; }
  /* Source credit pinned just above the footer band */
  .srcref { position: absolute !important; left: 0; right: 0; bottom: 40px;
            text-align: center; font-size: 16px !important; color: #5a6b75; }
  .slide-vcenter {
    display: flex !important; flex-direction: column !important;
    justify-content: center !important; height: 100% !important;
  }
  /* Positioning helpers — see references/positioning.md.
     These are div/img classes. A section `_class: foo` also works (marpit does
     attrJoin('class', …), so `section.foo{}` DOES match in static export), but for a
     one-slide override prefer <style scoped>section{padding:0!important}</style> —
     it is verified not to leak to other slides. */
  /* Multi-panel figure grids: apply to the WRAPPER div, e.g. <div class="panel-grid-2"> */
  .panel-grid-2 {
    display: grid !important; grid-template-columns: repeat(2, minmax(0,1fr)) !important;
    gap: 1.5rem !important; place-items: center !important;
  }
  .panel-grid-3 {
    display: grid !important; grid-template-columns: repeat(3, minmax(0,1fr)) !important;
    gap: 1rem !important; place-items: center !important;
  }
  .panel-grid-2 img, .panel-grid-3 img { max-width: 100%; max-height: 100%; object-fit: contain; }
  /* Place images by keyword in their alt text, e.g. ![top-right w:120](logo.png).
     Global img selectors, so they DO survive static export.
     Pattern from Miriam Müller's Marp cheatsheet (see positioning.md credits). */
  img[alt~="top-right"]     { position: absolute !important; top: 30px; right: 30px; margin: 0; }
  img[alt~="top-left"]      { position: absolute !important; top: 30px; left: 30px; margin: 0; }
  img[alt~="bottom-right"]  { position: absolute !important; bottom: 30px; right: 30px; margin: 0; }
  img[alt~="bottom-left"]   { position: absolute !important; bottom: 30px; left: 30px; margin: 0; }
---
```

Notes:
- Change `footer:` to the talk's venue.
- The `h1 { font-size: 1.8em }` variant (from the Soglio workshop deck) is fine for vignette decks where titles use `#`/`###`; the version above assumes `##` titles, which is the research-talk default.
- Don't trim classes you're not using yet — keeping the full block means any pattern from `snippets.md` works without edits.
- For a UZH-branded talk, paste `uzh_frontmatter_corporate.yml` over the front matter instead. It is this block plus the verified UZH palette and typeface; every class above is defined in it, so the deck body needs no edits. See `uzh_house_style.md`.
