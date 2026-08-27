# Verifying a deck without rendering it

**Gilles is the visual verifier.** He runs `./build.sh watch` in one terminal, keeps
`http://localhost:8080/<deck>.md` open in a browser, and it reloads the instant you save
the `.md`. Your job is to edit the markdown and *tell him what to look at*. Rendering to
"check" a layout yourself is slower than he is and it breaks his preview — see the next
section. Everything below replaces the render.

## Never run a second marp process

marp-cli drives a headless browser to produce images. What is actually measured on this
machine:

- a clean **HTML build is ~1.4 s** (no image export, so it is genuinely cheap);
- an **image export takes over 3 minutes for a *single* slide**, and a full-deck PNG
  export takes many minutes.

**The cost is in the image export, not in Chrome specifically.** The 3-minute single-slide
figure was reproduced with `--browser firefox` as well as Chrome, so **switching browsers
is a tested non-fix — do not try it again.** An earlier diagnosis blaming contention over
one shared Chrome was wrong and should not be reinstated.

Concurrency does make it dramatically worse, and is worth avoiding on its own:

- Observed failure: **6 concurrent marp processes turned 1-second builds into 5+ minute
  hangs**, and one process sat stuck for **over an hour**. The user's live preview stalled
  the whole time.

**Untested but most likely remaining cause:** a temp excerpt deck written *into the
directory the watch server watches* is picked up and converted by that server too — temp
files have been seen appearing in its served file index. If you ever do render, write the
temp deck to a scratch directory outside the repo.

Rules:

- **Do not render at all while Gilles is watching.** Edit, save, tell him which slide to look at.
- Treat rendering as **unavailable**, not merely discouraged: even a one-slide export
  blew past three minutes, so there is no working "quick peek". If you attempt one anyway,
  splice a **small excerpt deck** onto the same front matter (see below), write it to a
  scratch dir **outside** the watched directory, and never render the full deck.
- When you genuinely need eyes on a slide, the cheap routes are: **ask Gilles to paste a
  screenshot** (he already has it open), or drive his existing browser via the
  Claude-in-Chrome extension if connected. Neither starts a new browser.
- **One marp process at a time. Ever.** Strictly sequential, no `&`, no parallel tool calls.
- Check before and after any marp work:
  ```bash
  ps aux | grep '[m]arp/bin/marp'
  ```
- Kill *your own* orphans by matching the specific command line, never by killing all marp:
  ```bash
  pkill -f "images png _chk.md"     # yes: only the excerpt render you started
  pkill -f "marp/bin/marp"          # ONLY if no --watch --server of the user's is running
  ```
  **Never kill a `--watch --server` process** — that is the user's live preview, and it is
  probably the one thing he has open on the second monitor.
- **Subagents are a hazard here.** In one session a subagent was explicitly told "render
  6-slide excerpts, strictly sequentially" and still spawned parallel full-deck PNG exports
  that poisoned the machine for an hour. If you delegate any render work: give a hard
  numeric limit ("at most 1 marp process, at most 6 slides"), forbid background/parallel
  execution in the prompt, and check `ps` yourself afterwards.

If you must render an excerpt, splice the slides you care about onto the deck's own front
matter (so the styling is identical) and render *that* file — see `styles/make_variants.py`
in `presentations/2026/agentic_ai_in_cogneuro/` for the pattern.

## The cheap checks (each ~0.1 s — run these instead)

All of them start from the same two-line split. Put this in a scratch script, not in the repo.

```python
import re
from pathlib import Path

DECK = Path("agentic_ai_in_cogneuro.md")          # <- the deck
text  = DECK.read_text(encoding="utf-8")
end   = text.index("\n---\n", 3) + len("\n---\n")  # end of the YAML front matter
fm, body = text[:end], text[end:]
slides   = body.split("\n---\n")                   # slide 1 == slides[0]
```

### 1. Slide count + per-slide titles

The single most useful check: it tells you the deck length, and a `(no title)` line is
almost always a slide you broke by mis-splitting `---`.

```python
for i, s in enumerate(slides, 1):
    m = re.search(r"^#{1,3} +(.+)$", s, re.M)
    print(f"{i:3d}  {m.group(1) if m else '(NO TITLE)'}")
print(len(slides), "slides")
```

### 2. Every figure reference resolves on disk

This caught a genuinely broken deck when a figure was renamed underneath us. A missing
image renders as nothing at all in MARP — silent, and invisible unless you happen to look
at that slide.

```python
refs = re.findall(r'(?:!\[[^\]]*\]\(|src=")((?:figures|resources)/[^)"]+)', body)
missing = [r for r in dict.fromkeys(refs) if not (DECK.parent / r).exists()]
print(f"{len(set(refs))} refs · missing:", missing or "none")
```

It also picks up refs inside HTML comments (a commented-out `<video>` fallback, say), so
grep each hit in the source before calling it broken. Typical real hit: `.jpg` in the deck,
`.svg` on disk, because the figure was regenerated in another format.

### 3. `<div>` / `</div>` balance, per slide

An unbalanced div swallows the rest of the slide (or the rest of the deck).

```python
for i, s in enumerate(slides, 1):
    o, c = s.count("<div"), s.count("</div>")
    if o != c:
        print(f"slide {i}: {o} <div> vs {c} </div>")
```

### 4. Layout-trap lint

Each rule here is one of the traps in `marp_layout_gotchas.md`, made mechanical.

```python
def lint(slides):
    for i, s in enumerate(slides, 1):
        say = lambda m: print(f"slide {i:3d}  {m}")
        if re.search(r"!\[[^\]]*\b(?:width|height|w|h):\s*\d+(?:vh|vw|em|%)", s):
            say("image sized in non-px units -> hint falls through to alt text, image renders huge")
        if 'class="col' in s:
            for alt in re.findall(r"!\[([^\]]*height:\d+px[^\]]*)\]", s):
                say(f"height-sized image inside a column ({alt}) -> white letterbox bands if landscape")
        if re.search(r"^\s*> ", s, re.M):
            say("blockquote -> gaia adds its own quote glyphs; use a styled <div> instead")
        for c in re.findall(r"<!--.*?-->", s, re.S):
            if "--" in c[4:-3]:
                say("'--' inside an HTML comment -> the comment can terminate early")
        if re.search(r"<div[^>]*>\n(?!\n)[^<\n]", s):
            say("no blank line after <div> -> inner markdown leaks as literal text")
        if re.search(r"<div[^>]*>[^\n]*\*\*", s):
            say("**bold** on the same line as <div> -> renders as literal asterisks")
        for h in map(int, re.findall(r"!\[[^\]]*height:(\d+)px", s)):
            if h > 395 and re.search(r'class="[^"]*text-(?:small|tiny)', s):
                say(f"height:{h}px + a caption -> caption lands on the footer (keep <=395px)")

lint(slides)
```

### 5. Every helper class the body uses is defined in the style block

Catches a pasted snippet that relies on a class this deck's block doesn't have, and catches
typos (`.two-col--30-70` vs `--3070`).

```python
used = {c for grp in re.findall(r'class="([^"]+)"', body) for c in grp.split()}
defined = set(re.findall(r"\.([A-Za-z][\w-]*)", fm))
print("classes used but not in the style block:", sorted(used - defined) or "none")
```

## What still needs a human (or, rarely, a render)

- Whether a figure is *legible* at slide size.
- Whether a two-col split feels balanced.
- Whether a colour reads on a washed-out projector.

Those are Gilles's call, in the browser. Ask him to look; don't render behind his back.
