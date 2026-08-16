#!/usr/bin/env python3
"""Persistent pycortex webshow launcher template.

Run this with the harness's background-task mechanism (not `cmd & disown`
inside a single shell call — many sandboxes reap the whole process group
when the tool call returns, killing a merely-disowned child with it).

Works around two pycortex gotchas (see ../SKILL.md for the full writeup):

  1. cortex.webgl.show()'s auto-opened URL uses the machine hostname
     (serve.hostname), which frequently fails to resolve/connect in a
     browser. We force a plain `localhost` URL instead and open it
     ourselves.
  2. The Tornado server thread is daemon=True, so it dies the instant the
     calling Python process's main thread returns. We block forever after
     starting the server so it survives independent of the launching
     script's own control flow.

Usage: fill in the `# --- build your dataset(s) here ---` section, then:

    conda activate pycortex2   # or your project's light viewing env
    python persistent_webshow.py

(launched via a background-task runner, not manual `&`/disown).
"""
import subprocess
import time

import cortex

# --- build your dataset(s) here -------------------------------------------
# `ds` must be a dict of {label: Vertex | VertexRGB | Volume | ...}.
# If you're merging several helper functions that each internally call
# cortex.webgl.show(ds_i) themselves (rather than returning ds_i), capture
# with a monkeypatch instead of editing each function:
#
#     merged_ds = {}
#     def fake_show(data, **kwargs):
#         merged_ds.update(data)
#     cortex.webgl.show = fake_show
#     my_module.main(...)          # calls cortex.webgl.show(ds_a) internally
#     my_module.main_other(...)    # calls cortex.webgl.show(ds_b) internally
#     ds = merged_ds
#     import importlib; importlib.reload(cortex.webgl)   # restore real show()

ds = {}
raise NotImplementedError("fill in `ds` above before running")
# ----------------------------------------------------------------------------

server = cortex.webgl.show(ds, open_browser=False, autoclose=False)

port = server.port
url = f"http://localhost:{port}/mixer.html"
print(f"\n=== WEBSHOW READY ===\nOpen this URL:  {url}\n======================\n",
      flush=True)
subprocess.run(["open", url])          # macOS; drop or swap for other OSes

while True:
    time.sleep(3600)
