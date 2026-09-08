# gilles-claude-skills

A collection of [Claude skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) I use across my research, writing, and infrastructure work. They encode opinionated conventions for figure-making, statistical modelling, scientific writing, and a few personal workflows.

I'm a postdoc at the [Zurich Center for Neuroeconomics](https://www.econ.uzh.ch/en/research/neuroeconomics.html) (University of Zurich), working on perceptual distortions of magnitude representations and their consequences for economic decision-making. Most of these skills reflect that context — vision science, computational modelling, hierarchical Bayesian inference — but several are general enough to be useful outside it.

## Skills in this repo

| Skill | What it does |
| --- | --- |
| [`scientific-figures`](./skills/scientific-figures/) | Publication-quality scientific figures in a restrained, vision-science-inflected house style. Seaborn-on-matplotlib, Helvetica, despined and offset, in-panel annotations, PyMC/`bauer` posterior plotting with HDI credible intervals. |
| [`scientific-presentations`](./skills/scientific-presentations/) | Scientific talk decks in a figure-forward MARP house style — the gaia theme plus a shared CSS style block and helper classes, an outline-first workflow with per-slide speaker notes, deck-structure and citation conventions, and a `marp-cli` build script. Ships drop-in UZH corporate-design front matters plus layout/positioning gotchas and verification steps in [`references/`](./skills/scientific-presentations/references/). Pairs with [`scientific-figures`](./skills/scientific-figures/), which makes the figures the deck displays. |
| [`bayesian-workflow`](./skills/bayesian-workflow/) | Fitting and checking hierarchical Bayesian and cognitive models with PyMC / NumPyro / arviz / [`bauer`](https://github.com/Gilles86/bauer) — an order of operations that refuses to interpret a fit before it earns it, convergence triage (divergences vs r_hat vs max-treedepth saturation, and which of them `target_accept` can actually fix), identifiability and parameter recovery, LOO/WAIC comparison, and the sampler traps that cost days (NumPyro `chain_method="parallel"` silently serialising on CPU, `pm.Potential` breaking `log_likelihood` *after* sampling, JAX static-shape failures that only appear in hierarchical fits). References cover [building a PPC that can fail](./skills/bayesian-workflow/references/ppc_construction.md) and [sampler/backend traps](./skills/bayesian-workflow/references/sampler_traps.md). Pairs with [`scientific-figures`](./skills/scientific-figures/), which draws the result. |
| [`sciencecluster`](./skills/sciencecluster/) | UZH sciencecluster SLURM operational knowledge — submitting jobs, conda activation in SLURM context, GPU constraints (`--gres`, L4/V100/A100, cuInit-race stagger), `~/logs/` convention, common failure modes (`ArrayTaskThrottle` for NFS dogpile, `DependencyNeverSatisfied` zombies, walltime priority), and cluster-vs-local code paths. Ships with copy-pasteable SLURM templates in [`references/`](./skills/sciencecluster/references/): CPU array, GPU array, and an `afterok` chain orchestrator. |
| [`cogneuro-project`](./skills/cogneuro-project/) | House style for organizing cognitive-neuroscience fMRI projects — flat-package layout, `Subject` class as single source of truth (with NIfTI dtype guard against the uint8 `scl_slope` trap), pipeline-stage submodules (`prepare/`, `glm/`, `modeling/`, `behavior/`, ...), co-located SLURM wrappers, multi-env conda (`create_env/`), `notes/` markdown discipline, and conventions for using the in-house [`braincoder`](https://github.com/Gilles86/braincoder) (PRF/encoding) and [`bauer`](https://github.com/Gilles86/bauer) (Bayesian behavioral) libraries. Ships with copy-pasteable templates in [`references/`](./skills/cogneuro-project/references/): `Subject` skeleton, `CLAUDE.md` template, conda envs, CLI script, orchestrator, and worked braincoder/bauer fit examples. |
| [`fmriprep`](./skills/fmriprep/) | Operational knowledge for running fmriprep — healthy resource settings, the nipype `/scratch` cache trap and how to force a true clean rerun, why `--bold2anat-init` doesn't always take effect, treating the NIfTI output (not the HTML report) as ground truth, and visual coregistration QA. Fires when fmriprep finishes suspiciously fast or downstream tools (neuropythy, GLMsingle) error on missing FreeSurfer / cortical-ribbon files. Pairs with [`sciencecluster`](./skills/sciencecluster/) and [`cogneuro-project`](./skills/cogneuro-project/). |
| [`spm-glm`](./skills/spm-glm/) | Running and auditing SPM12 GLMs driven by nipype — the parametric-modulator orthogonalisation trap (SPM orthogonalises serially by default, nipype silently drops `Bunch.orth`, and the map that moves is the *first* modulator's, not the residualised one), verifying a design from `SPM.mat`, SnPM `ST_later` threshold sweeps that need no re-permutation, comparing contrast images by data rather than checksum, and measured SLURM sizing for MATLAB/SPM jobs. Pairs with [`sciencecluster`](./skills/sciencecluster/). |
| [`pycortex`](./skills/pycortex/) | Gotchas and best practices for pycortex cortical-surface visualization — why `cortex.webgl.show()` "doesn't load" (the server's daemon thread dies the instant the script exits; the auto-opened URL uses the machine hostname, not localhost), the `pycortex2`-vs-heavy-env split, `VertexRGB`/`blend_curvature` vs `Vertex2D` for alpha and thresholding (baked-in vs live), why R²-shaped auto-threshold code silently breaks on cvR² that can go negative, and the `make_static` traps (never put `"flat"` in `types`; stale payloads accumulate). Ships a persistent-viewer launcher and a static-bundle-plus-colorbar script in [`references/`](./skills/pycortex/references/). |
| [`eyetracking-edf`](./skills/eyetracking-edf/) | Parsing SR Research EyeLink `.edf` files on a SLURM cluster — the Linux-only `edf2asc` constraint, the two-pass ASCII conversion (events vs. raw samples), trial/phase onsets from exptools2-style MSG lines, and the step everyone gets wrong: deriving the pixel→degrees conversion from the per-run experiment-settings log instead of hardcoding screen geometry. Pairs with [`sciencecluster`](./skills/sciencecluster/). |
| [`snakemake`](./skills/snakemake/) | Practical Snakemake-on-SLURM knowledge — driver placement (in `sbatch`, never on the login node), rule-output conventions for per-wildcard outputs, monitoring via the SLURM `--comment` field, recovery from crashed drivers (`--rerun-incomplete`), and `rerun-triggers: input` to stop forward-cascade reruns. Pairs with [`sciencecluster`](./skills/sciencecluster/). |
| [`data-archival`](./skills/data-archival/) | Safely archiving and deleting large research datasets across a two-tier backup setup — a compute cluster as canonical big-data archive plus an institutional SMB share as the official per-project archive. Verify-before-delete with checksums, the macOS openrsync + flaky-SMB-mount pitfalls, and an audit→back-up→delete workflow with hard rules against unapproved deletion. Ships a project→archive map template in [`references/`](./skills/data-archival/references/); your actual map belongs in private notes, not here. |

More to come — likely candidates include grant-writing voice and citation style.

## Installing

Skills are just directories containing a `SKILL.md` file. To use them with Claude Code, clone the repo and run the install script:

```bash
git clone https://github.com/Gilles86/gilles-claude-skills.git
cd gilles-claude-skills
./install.sh
```

`install.sh` symlinks every skill under `skills/` into `~/.claude/skills/` (or `$CLAUDE_SKILLS_DIR` if set). It's idempotent — re-run after `git pull` to pick up newly added skills, and existing non-symlink entries are left alone with a warning rather than clobbered.

If you only want one skill, link it by hand:

```bash
ln -s "$(pwd)/skills/scientific-figures" ~/.claude/skills/scientific-figures
```

## Using

Once installed, Claude Code will load a skill automatically when its description matches what you're asking for. For example, asking Claude to "make a figure of the psychometric curve fits" will trigger `scientific-figures` if it's installed, and Claude will follow the conventions encoded there.

You don't need to invoke skills by name — they fire on relevance. If a skill isn't triggering when you expect it to, check that the description in its `SKILL.md` covers the use case you have in mind.

## Contributing

These are my personal house-style skills, so I'm not soliciting pull requests in the usual sense — but if you spot a bug, a contradiction, or something that's flat-out wrong, open an issue and I'll take a look. Fork freely if you want to adapt any of these to your own style.

## License

MIT — see [LICENSE](./LICENSE). Use, modify, and redistribute as you like. Attribution appreciated but not required.

## Acknowledgements

The aesthetic conventions in `scientific-figures` draw on years of looking at carefully made vision-science and psychophysics figures, as well as conversations with collaborators and mentors. The encoding into a skill is mine; errors and infelicities are mine too.
