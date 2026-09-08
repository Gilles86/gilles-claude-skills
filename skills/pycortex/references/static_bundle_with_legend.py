"""Static pycortex bundle + a colorbar legend the viewer cannot draw itself.

Reference implementation extracted from abstract_values
(``abstract_values/visualize/webshow_surface_maps.py``). Two problems it solves:

1. ``cortex.webgl.show()`` dies with the launching process (see
   ``persistent_webshow.py``). ``cortex.webgl.make_static()`` writes plain
   HTML/JS/binary instead, servable by ``python -m http.server`` from
   anywhere, rsyncable, and reopenable without rebuilding the datasets.

2. ``blend_curvature()`` pre-blends data and curvature into one RGB image, so
   pycortex has no live vmin/vmax/cmap left and its own colorbar is a
   meaningless 0-255 swatch. Rather than give up the good compositing for
   ``Vertex2D`` (whose shader-side alpha looks washed out), draw the legend
   yourself from the ranges you already hold and inject it into the page.

The injected panel tracks the active dataset by wrapping
``mriview.Viewer.prototype.setData`` — the single funnel every dataset switch
goes through. Notes that cost real debugging time:

* pycortex's generated page closes neither ``</body>`` nor ``</html>``, so the
  panel is appended and the browser reparents it.
* pycortex selects the first dataset during load, before the wrapper can be
  installed, so also probe the implicit global ``figure`` for the active view.
* ``make_static`` never deletes files it did not write this run. Rebuilding
  with a different dataset list leaves the old payloads behind — unreferenced
  but accumulating (one bundle reached 235 MB against 85 MB clean). Clear
  ``<dir>/data/`` first.
* ``types`` is for MORPH TARGETS only. Never put ``"flat"`` in it: pycortex
  loads the flat surface itself and stores it as UV (that is what drives the
  flatten slider), while ``addSurf("flat")`` renormalises it into the fiducial
  bounding box, and the flat z axis is constant — so it divides by zero and
  OpenCTM rejects the mesh with a bare ``CTM_INVALID_MESH``.
* A BrainData's ``name`` is a read-only hash of its array and
  ``Package.reorder`` is not dedup-aware: two datasets handing it identical
  arrays crash with ``TypeError: byte indices must be integers or slices, not
  tuple``, which names nothing useful. De-duplicate before showing.

Usage sketch::

    ds = {"My map (unsmoothed)": cortex.Vertex(vals, subj, vmin=0, vmax=1,
                                               cmap="hot").blend_curvature(alpha)}
    cbars = [("My map", "hot", 0.0, 1.0)]        # (label, cmap, vmin, vmax)

    out = Path("/tmp/bundle/sub-01"); out.mkdir(parents=True, exist_ok=True)
    for stale in (out / "data").glob("*"):
        stale.unlink()
    cortex.webgl.make_static(str(out), ds, types=("inflated",), recache=False,
                             curvature_brightness=0.62, curvature_contrast=0.28,
                             curvature_smoothness=2.0)
    inject_legend(out / "index.html", list(ds), cbars)
    write_root_index(out.parent)                  # landing page over sub-*/group/...
    serve_directory(out.parent, 8000)
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import cortex
import matplotlib.pyplot as plt
import numpy as np


def _gradient_css(cmap, n=24):
    """CSS linear-gradient approximating a matplotlib colormap."""
    import matplotlib as _mpl
    import matplotlib.pyplot as _plt
    # Callers may pass a name or an already-built Colormap (the categorical
    # winner map builds a ListedColormap on the fly).
    cm = cmap if isinstance(cmap, _mpl.colors.Colormap) else _plt.get_cmap(cmap)
    cols = cm(np.linspace(0, 1, n))[:, :3]
    stops = ", ".join(
        "rgb(%d,%d,%d)" % tuple(int(round(255 * c)) for c in row) for row in cols)
    return f"linear-gradient(to right, {stops})"


def inject_legend(index_html, names, cbars):
    """Add a colorbar panel to a make_static page that follows the active map.

    blend_curvature bakes data and curvature into one RGB image, which is what
    makes these maps read well against the anatomy — but it leaves pycortex no
    vmin/vmax/cmap to build a colorbar from. So draw the legend ourselves from
    the ranges we already hold, and show only the map currently on screen:
    with both smoothing variants there are 16 of them, and a wall of scales is
    no more use than none.

    Tracking is done by wrapping ``mriview.Viewer.prototype.setData`` — the
    single funnel every dataset switch goes through, whether it came from the
    dropdown, a keypress or the URL. If that global is ever missing the panel
    falls back to listing everything rather than showing nothing.
    """
    index_html = Path(index_html)
    html = index_html.read_text()
    if 'id="aprf-legend"' in html:
        return
    entries = {
        name: {"cmap": _gradient_css(cmap), "label": label,
               "vmin": f"{vmin:.3g}", "vmax": f"{vmax:.3g}"}
        for name, (label, cmap, vmin, vmax) in zip(names, cbars)}

    panel = """
<style>
#aprf-legend { position: fixed; right: 20px; bottom: 20px; z-index: 10000;
  font: 16px/1.45 -apple-system, system-ui, sans-serif; color: #f2f2f2;
  background: rgba(18,18,18,.92); border: 1px solid #4a4a4a; border-radius: 10px;
  padding: 16px 20px 18px; width: 30vw; min-width: 380px; max-width: 620px;
  box-shadow: 0 6px 24px rgba(0,0,0,.45); }
#aprf-legend .cb-name { font-size: 17px; font-weight: 600; color: #fff;
  margin-bottom: 10px; line-height: 1.25; }
#aprf-legend .cb-bar { height: 30px; border-radius: 4px; border: 1px solid #666; }
#aprf-legend .cb-lim { display: flex; justify-content: space-between;
  align-items: baseline; font-size: 14px; color: #b6b6b6;
  font-variant-numeric: tabular-nums; margin-top: 7px; gap: 14px; }
#aprf-legend .cb-lim b { color: #f2f2f2; font-weight: 500; font-size: 13px;
  text-align: center; }
#aprf-legend.all { max-height: 72vh; overflow-y: auto; }
#aprf-legend.all .cb { margin-bottom: 18px; }
#aprf-legend.all .cb-name { font-size: 14px; margin-bottom: 6px; }
#aprf-legend.all .cb-bar { height: 20px; }
#aprf-toggle { float: right; cursor: pointer; color: #cfcfcf; font-size: 13px;
  border: 1px solid #666; border-radius: 5px; padding: 3px 10px;
  margin: -4px -6px 0 10px; user-select: none; }
#aprf-toggle:hover { color: #fff; border-color: #999; background: rgba(255,255,255,.08); }
</style>
<div id="aprf-legend"><span id="aprf-toggle">all</span><div id="aprf-body"></div></div>
<script>
(function () {
  var CB = __ENTRIES__;
  var showAll = false, current = null;
  function row(name, e) {
    return '<div class="cb"><div class="cb-name">' + name + '</div>' +
           '<div class="cb-bar" style="background:' + e.cmap + '"></div>' +
           '<div class="cb-lim"><span>' + e.vmin + '</span><b>' + e.label +
           '</b><span>' + e.vmax + '</span></div></div>';
  }
  function render() {
    var body = document.getElementById('aprf-body');
    var panel = document.getElementById('aprf-legend');
    if (!body) return;
    if (showAll) {
      panel.className = 'all';
      body.innerHTML = Object.keys(CB).map(function (k) { return row(k, CB[k]); }).join('');
    } else {
      panel.className = '';
      var k = (current && CB[current]) ? current : Object.keys(CB)[0];
      body.innerHTML = CB[k] ? row(k, CB[k])
        : '<div class="cb-name">No map selected</div>';
    }
  }
  function setCurrent(name) {
    if (name instanceof Array) name = name[0];
    current = name;
    if (!showAll) render();
  }
  // pycortex selects the first dataset during load, which happens before the
  // hook below is installed — so read the active view directly rather than
  // showing nothing until the user switches. `figure` is an implicit global
  // (assigned without var in the generated page).
  function probe() {
    try {
      var roots = [typeof figure !== 'undefined' ? figure : null];
      for (var i = 0; i < roots.length; i++) {
        var r = roots[i];
        if (!r) continue;
        if (r.active && r.active.name) return r.active.name;
        for (var k in r) {
          var c = r[k];
          if (c && c.active && c.active.name) return c.active.name;
        }
      }
    } catch (err) {}
    return null;
  }
  document.addEventListener('DOMContentLoaded', function () {
    var t = document.getElementById('aprf-toggle');
    if (t) t.onclick = function () { showAll = !showAll; t.textContent = showAll ? 'one' : 'all'; render(); };
    render();
  });
  // Wrap the single funnel every dataset switch goes through.
  var tries = 0;
  var iv = setInterval(function () {
    if (typeof mriview !== 'undefined' && mriview.Viewer && mriview.Viewer.prototype.setData) {
      clearInterval(iv);
      var orig = mriview.Viewer.prototype.setData;
      mriview.Viewer.prototype.setData = function (name) {
        var r = orig.apply(this, arguments);
        try { setCurrent(this.active ? this.active.name : name); } catch (err) { setCurrent(name); }
        return r;
      };
      var found = probe();
      if (found) setCurrent(found);
    } else if (++tries > 100) {   // ~10 s; viewer never appeared
      clearInterval(iv);
      showAll = true;
      var t = document.getElementById('aprf-toggle');
      if (t) t.textContent = 'one';
      render();
    }
  }, 100);
})();
</script>
"""
    panel = panel.replace("__ENTRIES__", json.dumps(entries))
    marker = "</body>"
    html = (html.replace(marker, panel + marker) if marker in html
            else html + panel)
    index_html.write_text(html)
    print(f"  injected a tracking legend for {len(entries)} maps "
          f"into {index_html.name}")


def write_root_index(root):
    """Generate a landing page listing every subject bundle under `root`.

    http.server's own directory listing works, but it shows the raw folder
    names and gives no hint which bundles are stale. This lists subjects in
    the project's usual order (numeric first, pilots last) with the date each
    bundle was built.
    """
    root = Path(root)
    rows = []
    for d in sorted(x for x in root.iterdir() if x.is_dir()):
        idx = d / "index.html"
        if not idx.exists():
            continue
        label = d.name.removeprefix("sub-")
        built = datetime.fromtimestamp(idx.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        rows.append((label, d.name, built, size / 1e6))

    # cohort-level bundles first, then study subjects numerically, pilots last
    titles = {"group": "Group (all subjects)",
              "r2-browser": "R² browser (every subject, both models)"}
    order = {"group": -2, "r2-browser": -1}

    def sort_key(r):
        if r[1] in order:
            return (order[r[1]], 0)
        return (0, int(r[0])) if r[0].isdigit() else (1, 0)

    rows.sort(key=sort_key)

    items = "\n".join(
        f'      <li><a href="{name}/index.html">'
        f'{titles.get(name, f"sub-{label}")}</a>'
        f'<span>{built} &middot; {mb:.0f} MB</span></li>'
        for label, name, built, mb in rows)
    html = f"""<!doctype html>
<meta charset="utf-8">
<title>aPRF surface maps</title>
<style>
  body {{ font: 15px/1.5 -apple-system, system-ui, sans-serif; margin: 3rem auto;
         max-width: 40rem; color: #222; }}
  h1 {{ font-size: 1.25rem; font-weight: 600; }}
  p.sub {{ color: #666; margin-top: -0.5rem; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ display: flex; justify-content: space-between; align-items: baseline;
        padding: 0.5rem 0; border-bottom: 1px solid #eee; }}
  a {{ text-decoration: none; color: #1a5fb4; font-weight: 500; }}
  a:hover {{ text-decoration: underline; }}
  span {{ color: #888; font-size: 0.85em; font-variant-numeric: tabular-nums; }}
</style>
<h1>aPRF surface maps</h1>
<p class="sub">{len(rows)} subject bundle(s), individual (fsnative) space.</p>
<ul>
{items}
</ul>
"""
    (root / "index.html").write_text(html)
    print(f"Wrote root index ({len(rows)} subjects) -> {root / 'index.html'}")
    return root / "index.html"


def serve_directory(directory, port):
    """Serve `directory` over HTTP until interrupted, and open a browser."""
    import functools
    import http.server
    import socketserver

    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        url = f"http://localhost:{port}/index.html"
        print(f"\n=== SERVING ===\nOpen this URL:  {url}\n"
              f"Serving {directory}\n===============\n", flush=True)
        subprocess.run(["open", url])
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
