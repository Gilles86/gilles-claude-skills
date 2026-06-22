# build.sh template

MARP is run via `marp-cli` installed in a dedicated `marp` conda env at `~/mambaforge/envs/marp/bin`. Drop this `build.sh` at the deck's repo root, `chmod +x build.sh`, and set `DECK` to the deck filename.

> **CRITICAL: pass `--html` to every marp invocation.** Without it, marp-cli sanitizes raw HTML and **silently strips inline `style`/`id` attributes from your tags** (`class` survives, and so does MARP's own `![w:..]` image sizing — which is why bugs hide: *some* things still work). Every `<div style="display:flex…">`, every absolute-positioned box, every `<video width=…>` quietly loses its attributes and your layout collapses to default flow. The front-matter `html: true` directive does **not** fix this — it must be the CLI flag. (VS Code's Marp preview enables HTML by default, so a layout that "works in preview" can still break in the `build.sh` export until you add `--html`.) This one flag was the root cause of an entire afternoon of "why won't this center" debugging.

```bash
#!/usr/bin/env bash
# Build the talk deck. Uses marp-cli from the `marp` conda env.
set -e
DECK="my_talk.md"
MARP_BIN="$HOME/mambaforge/envs/marp/bin"
export PATH="$MARP_BIN:$PATH"
MARP="$MARP_BIN/marp"
# --html is REQUIRED (keeps inline style/id); --allow-local-files embeds images/video.
HTML="--html --allow-local-files"

case "${1:-html}" in
  html)   "$MARP" $HTML "$DECK" -o "${DECK%.md}.html" ;;
  pdf)    "$MARP" $HTML --pdf  "$DECK" -o "${DECK%.md}.pdf" ;;
  pptx)   "$MARP" $HTML --pptx "$DECK" -o "${DECK%.md}.pptx" ;;
  png)    "$MARP" $HTML --images png "$DECK" -o "slide.png" ;;
  watch)  "$MARP" $HTML --watch --server . ;;
  all)    "$0" html && "$0" pdf ;;
  *)      echo "Usage: $0 {html|pdf|pptx|png|watch|all}"; exit 1 ;;
esac
```

Usage:
- `./build.sh` or `./build.sh html` — render HTML (self-contained; good default).
- `./build.sh pdf` — PDF for sharing / backup at the podium.
- `./build.sh pptx` — PowerPoint if a venue requires it.
- `./build.sh watch` — live server with auto-reload while editing (the iterate loop).
- `./build.sh all` — html + pdf.

Notes:
- **`--allow-local-files` is mandatory** — without it MARP won't embed local images/video and they render blank.
- If the `marp` env doesn't exist yet: `conda create -n marp -c conda-forge nodejs && conda run -n marp npm install -g @marp-team/marp-cli`. (Or install marp-cli however convenient and point `MARP_BIN` at it.)
- PDF export uses headless Chromium under the hood; first run may download it.
- Videos only play in the **HTML** output, not PDF/PPTX — keep a static fallback image for the PDF if a video slide carries essential content.
