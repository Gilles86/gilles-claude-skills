# The figure refinement pipeline — reusable scaffolding

Recipes for the iterative refinement loop described in the main skill: a
render-on-save watcher (so nobody runs a render command), a contact sheet (for
the rare all-at-once look), and an export verifier (the objective gate). All are
project-agnostic templates — adapt the three CONFIG lines at the top of each.

The point of all three: keep the **user** as the aesthetic judge with a live
preview, and keep the assistant as editor + objective QA. Don't rasterize-and-
read on every tweak.

---

## 1. Render-on-save watcher (`watch.sh`)

Requires one of `watchexec` (nicest), `entr`, or `fswatch`. Renders the
most-recently-modified script on each save, so there's no fragile change-event
parsing; a shared style/verify module re-renders everything.

```bash
#!/usr/bin/env bash
# Live-render figure PDFs on save. Run in its own terminal:  ./watch.sh
# Then edit any <figdir>/figure_*.py and save -- its PDF refreshes; the PDF
# viewer (Preview/Affinity/IDE) shows it fresh on refocus.
set -uo pipefail

# --- CONFIG (adapt these three) ---------------------------------------------
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"   # repo root
PY="$HOME/mambaforge/envs/<env>/bin/python"                  # project's python
FIGDIR="$REPO/<package>/figures"                             # dir of figure_*.py
# Render one module. Adapt to however a single figure is built in this project
# (here: `python -m <package>.figures.<stem>`).
render_one () { ( cd "$REPO" && "$PY" -m "<package>.figures.$1" ); }
# ----------------------------------------------------------------------------

LOG=/tmp/figwatch.log
render_module () {
  printf '↻ %s … ' "$1"
  if render_one "$1" >"$LOG" 2>&1; then echo "✓"; else echo "✗"; tail -n 15 "$LOG"; fi
}
render_all () { for f in "$FIGDIR"/figure_*.py; do render_module "$(basename "$f" .py)"; done; }

# The most-recently-modified .py is the one just saved. Shared modules -> all.
on_change () {
  local newest stem
  newest="$(ls -t "$FIGDIR"/*.py 2>/dev/null | head -1)"; [ -z "$newest" ] && return
  stem="$(basename "$newest" .py)"
  case "$stem" in
    style|verify) render_all ;;
    figure_*)     render_module "$stem" ;;
    *)            : ;;
  esac
}

if [ "${1:-}" = "--once" ]; then on_change; exit 0; fi
command -v watchexec >/dev/null 2>&1 || { echo "need: brew install watchexec" >&2; exit 1; }
echo "👀 Watching $FIGDIR — edit a figure_*.py and save. Ctrl-C to stop."
exec watchexec --quiet --postpone --watch "$FIGDIR" --exts py --debounce 300ms -- "$0" --once
```

`entr` variant (no env-var plumbing needed either):
```bash
ls "$FIGDIR"/*.py | entr -p "$0" --once    # -p: run on change, not at startup
```

---

## 2. Contact sheet — see every panel in one image

For the rare holistic look (final QA, "what do you think of the set?"). Tiles all
panel PDFs into one labelled PNG, so you read **one** image instead of N. Needs
`imagemagick` (`montage`) and `sips` (macOS) or `pdftoppm` (poppler, cross-platform).

```bash
# PDF -> PNG (macOS sips; or: pdftoppm -png -r 150 "$f" "/tmp/fig_<name>")
for f in <figdir>/figure_*.pdf; do
  sips -s format png --resampleWidth 640 "$f" --out "/tmp/fig_$(basename "$f" .pdf).png" >/dev/null
done
# Tile 4-up, label each with its filename. The -font is needed on macOS or
# montage errors on the default label font.
montage /tmp/fig_*.png -font /System/Library/Fonts/Supplemental/Arial.ttf \
  -label '%t' -pointsize 12 -tile 4x -geometry 320x+5+16 -background white \
  /tmp/contact_sheet.png
```

---

## 3. Export verifier — the objective gate (`verify.py`)

The deterministic checks no human should eyeball: fonts embedded & editable (not
paths), correct font family, RGB (not CMYK), exact page size, line weights.
`pdffonts` (poppler) covers fonts/embedding in one line; page size / colour need
a PDF lib (`pypdf`). Min-font-size is the only hard one (needs content-stream
parsing) — sketch below.

Fonts + embedding, the highest-value check, as a shell one-liner:
```bash
# Every embedded font must be the house font (e.g. Helvetica) and "emb yes".
# A common violation: mathtext ($...$) pulls in STIX/DejaVu for fraction bars,
# Greek, or minus signs. Prefer Unicode in plain strings over mathtext.
for f in <figdir>/*.pdf; do
  bad=$(pdffonts "$f" | tail -n +3 | awk '{print $1}' | grep -vi helvetica)
  [ -n "$bad" ] && echo "$f: $bad"
done
echo "(no output above = all Helvetica)"
```

Page size (mm) + RGB, with `pypdf`:
```python
import pypdf
PT_PER_MM = 72 / 25.4
for path in sorted(glob.glob(f'{FIGDIR}/*.pdf')):
    page = pypdf.PdfReader(path).pages[0]
    w_mm = float(page.mediabox.width)  / PT_PER_MM
    h_mm = float(page.mediabox.height) / PT_PER_MM
    # Assert against the panel's target mm box; flag CMYK / separation colour
    # by scanning the resource /ColorSpace entries.
    print(f'{path}: {w_mm:.0f}×{h_mm:.0f} mm')
```

Min font size (the matrix-aware subtlety): when you walk text-showing operators,
the *rendered* size is the font size scaled by the text/CTM matrix, so a rotated
y-tick label (90°) has its height in the matrix's off-diagonal term. A naive
"font size" read mis-flags rotated labels as tiny. Use the larger of the two
relevant matrix terms (`max(|a|, |b|)` for the x-basis) when computing the
on-page glyph size, then compare against the journal floor (≥ 6 pt; design ≥ 7).
Libraries: `pdfminer.six` (`LTChar.matrix`) or `pikepdf` for content streams.

Run it once per refinement pass; it catches the regressions humans miss
(a label that slipped under the floor, a stray Type-3 font, a panel that drifted
off its mm box).
