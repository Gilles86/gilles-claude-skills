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
  .pullquote       { font-size: 36px !important; line-height: 1.25; font-style: italic; }
  .slide-vcenter {
    display: flex !important; flex-direction: column !important;
    justify-content: center !important; height: 100% !important;
  }
  /* Positioning helpers — see references/positioning.md.
     NOTE: these are div/img classes, NOT section _class hooks. _class emits
     data-class in static export so `section.foo{}` never matches — see
     marp_layout_gotchas.md. To zero padding for a full-bleed slide use
     <style scoped>section{padding:0!important}</style>, not a class. */
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
