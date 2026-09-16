# Code release: GitHub (`ruffgroup/<project>`) → Zenodo DOI

## 1. Repo home

The public home is `github.com/ruffgroup/<project>`. If the repo grew under a
personal account, **transfer** it (GitHub: Settings → Danger zone → Transfer)
rather than re-pushing: GitHub redirects the old URL and all clones/issues
follow. If an earlier preprint already cites the personal URL, keep the
personal repo as a mirror and say so in the README ("same repository, kept as
a mirror"). Update `origin` locally and in any cluster checkout.

## 2. Pre-public scrub (tree AND history)

Before flipping visibility to public, the archive Zenodo will take is
forever, so scrub first:

```bash
# was anything private ever committed?
git log --all --stat -- notes/ '*.env' '*secret*' '*.key' '*token*' | head
# personal paths, emails, hostnames in tracked files
grep -rnE '/Users/|/home/|/shares/|[A-Z]:\\\\|@[a-z0-9.-]+\.(ch|com|edu)|([0-9]{1,3}\.){3}[0-9]{1,3}' \
   --exclude='*.lock.yml' --exclude='*.ipynb' --exclude-dir=.git .
# large binaries that don't belong (data, traces, PDFs of the paper)
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob" && $3 > 5000000' | sort -k3 -n | tail
```

- `notes/` (reviewer letters, drafts, paper PDFs) must be gitignored **and**
  absent from history. If it was ever committed, rewrite with
  `git filter-repo --path notes/ --invert-paths` *before* the release, and
  force-push with the owner's explicit go — every collaborator re-clones.
- Reviewer-facing text in code comments ("as Reviewer 2 asked") — reword.
- Absolute personal paths as hard-coded defaults: replace with a documented
  convention or an env var.
- Secrets: API keys, `.netrc`, OpenNeuro/figshare tokens. If one was ever
  committed, rotate it *and* rewrite history.

## 3. Files the release needs

- `LICENSE` — MIT (or BSD-3) for code; stated in README and in `.zenodo.json`.
- `README.md` per `reproducibility_readme.md`.
- `CITATION.cff` — GitHub renders "Cite this repository"; Zenodo reads it
  as fallback metadata.
- `.zenodo.json` — overrides Zenodo's GitHub-derived metadata (which would
  otherwise list GitHub usernames as authors):

```json
{
  "title": "<project>: analysis code for '<paper title>'",
  "description": "<p>Analysis code for <authors> (<year>), <journal>. Reproduces every figure and statistic from the public data (OpenNeuro <ds>, figshare <doi>). See README.</p>",
  "creators": [
    {"name": "<Family>, <Given>", "orcid": "0000-0000-0000-0000", "affiliation": "<institution>"}
  ],
  "upload_type": "software",
  "access_right": "open",
  "license": "MIT",
  "keywords": ["fMRI", "population receptive field", "Bayesian decoding", "..."],
  "related_identifiers": [
    {"identifier": "10.xxxx/<paper-doi>",               "relation": "isSupplementTo",   "resource_type": "publication-article"},
    {"identifier": "10.18112/openneuro.ds00XXXX.v1.0.0", "relation": "isSupplementedBy", "resource_type": "dataset"},
    {"identifier": "10.6084/m9.figshare.XXXXXXX",        "relation": "isSupplementedBy", "resource_type": "dataset"},
    {"identifier": "10.5281/zenodo.<library-doi>",       "relation": "requires",         "resource_type": "software"}
  ]
}
```

Validate the JSON (`jq . .zenodo.json`) — a malformed file makes Zenodo fall
back to GitHub metadata silently.

## 4. Zenodo integration BEFORE the tag

1. zenodo.org → log in with GitHub → *GitHub* page → flip the toggle for
   `ruffgroup/<project>`. Requires admin on the org repo. Do this *before*
   creating the release; Zenodo only archives releases made after the toggle.
2. Make the final commit (README, lock files, `.zenodo.json`). This is the
   tree the smoke test passed on — if you change code after the smoke test,
   re-run it.
3. Tag and release:
   ```bash
   git tag -a v1.0.0 -m "Code as published in <journal> (<year>)"
   git push origin v1.0.0
   gh release create v1.0.0 --title "v1.0.0 — published version" --notes "See README for reproduction."
   ```
4. Zenodo picks up the release within minutes and mints **two DOIs**: a
   version DOI (`…zenodo.NNNNNN1`, this tag) and a concept DOI (`…NNNNNN0`,
   all versions). README badge and long-lived links use the **concept DOI**;
   the paper's Code Availability cites the **version DOI** (the exact tree).

The chicken-and-egg: the tagged tree cannot contain its own version DOI. Fine
— add the concept-DOI badge in a follow-up commit (it does not change the
archived code), or tag `v1.0.1` "adds DOI to README" if the journal insists
that the cited tag shows the DOI.

## 5. Submodules are NOT in the archive

GitHub's release tarball — and therefore the Zenodo archive — excludes
submodule contents. `libs/<lib>` (a Python package or a MATLAB toolbox alike)
arrives as an empty directory. Options,
in order of preference:

1. Pin the library commit in the env spec **and** cite the library's own
   Zenodo DOI (release the library from a tag at that commit if none exists).
   The README's `git clone --recursive` instruction covers the dev path.
2. Vendor a source tarball of the library at the pinned SHA into the release
   assets (`gh release upload v1.0.0 <lib>-<sha>.tar.gz`, or via the GitHub web UI) — Zenodo
   archives release assets too.

Never vendor a copy of the library *into the tree* — it will drift from the
submodule.

## 6. Tag the library too

```bash
git -C ~/git/<lib> tag -a <project>-paper <sha> -m "Version used for <project> (<journal> <year>)"
git -C ~/git/<lib> push origin <project>-paper
gh release create <project>-paper --repo <org>/<lib> --title "<lib> as used in <project>" --notes "..."   # → DOI if Zenodo is on
```

## 7. Statements (templates)

**Data availability.** "The neuroimaging data (raw BIDS[, and the derivatives
used in the paper]) are available on OpenNeuro as dataset dsXXXXXX
(https://doi.org/10.18112/openneuro.dsXXXXXX.v1.0.0), released under CC0.
Trial-level behavioural data and a codebook are available on figshare
(https://doi.org/10.6084/m9.figshare.XXXXXXX). [Eye-tracking / physiological
recordings are not shared because <reason>.] Source data for all figures are
provided with this paper."

**Code availability.** "All analysis code is available at
https://github.com/ruffgroup/<project> and archived on Zenodo
(https://doi.org/10.5281/zenodo.NNNNNNN, version v1.0.0). <Analysis step>
used <in-house library> (https://github.com/<org>/<lib>, commit `<sha>`,
https://doi.org/10.5281/zenodo.<lib-doi>)[; <other step> used <library> (…)].
Preprocessing used fMRIPrep <version> (RRID:SCR_016216)[; GLMs were estimated
in MATLAB R20xx with SPM12 r<rev> (RRID:SCR_007037)]. Pinned environment
specifications and full lock files are included in the repository."

## 8. Cross-link everything

| Artifact | Must mention |
|---|---|
| Paper statements | OpenNeuro DOI, figshare DOI, GitHub URL, Zenodo DOI, library DOIs/commits |
| README top block | same list, verbatim |
| `.zenodo.json` `related_identifiers` | paper DOI, both data DOIs, library DOI |
| OpenNeuro `dataset_description.json` `ReferencesAndLinks` | paper DOI, GitHub URL, Zenodo DOI, figshare DOI |
| figshare description | paper DOI, OpenNeuro DOI, GitHub URL |
| Library repo release notes | the paper DOI |

When the paper DOI is not yet known, use the preprint DOI and update all six
places when it is — one checklist row per artifact.
