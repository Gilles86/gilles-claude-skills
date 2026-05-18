# gilles-claude-skills

A collection of [Claude skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) I use across my research, writing, and infrastructure work. They encode opinionated conventions for figure-making, statistical modelling, scientific writing, and a few personal workflows.

I'm a postdoc at the [Zurich Center for Neuroeconomics](https://www.econ.uzh.ch/en/research/neuroeconomics.html) (University of Zurich), working on perceptual distortions of magnitude representations and their consequences for economic decision-making. Most of these skills reflect that context — vision science, computational modelling, hierarchical Bayesian inference — but several are general enough to be useful outside it.

## Skills in this repo

| Skill | What it does |
| --- | --- |
| [`scientific-figures`](./skills/scientific-figures/) | Publication-quality scientific figures in a restrained, vision-science-inflected house style. Seaborn-on-matplotlib, Helvetica, despined and offset, in-panel annotations, PyMC/`bauer` posterior plotting with HDI credible intervals. |
| [`sciencecluster`](./skills/sciencecluster/) | UZH sciencecluster SLURM operational knowledge — submitting jobs, conda activation in SLURM context, GPU constraints (`--gres`, L4/V100/A100, cuInit-race stagger), `~/logs/` convention, common failure modes (`ArrayTaskThrottle` for NFS dogpile, `DependencyNeverSatisfied` zombies, walltime priority), and cluster-vs-local code paths. Ships with copy-pasteable SLURM templates in [`references/`](./skills/sciencecluster/references/): CPU array, GPU array, and an `afterok` chain orchestrator. |
| [`cogneuro-project`](./skills/cogneuro-project/) | House style for organizing cognitive-neuroscience fMRI projects — flat-package layout, `Subject` class as single source of truth (with NIfTI dtype guard against the uint8 `scl_slope` trap), pipeline-stage submodules (`prepare/`, `glm/`, `modeling/`, `behavior/`, ...), co-located SLURM wrappers, multi-env conda (`create_env/`), `notes/` markdown discipline, and conventions for using the in-house [`braincoder`](https://github.com/Gilles86/braincoder) (PRF/encoding) and [`bauer`](https://github.com/Gilles86/bauer) (Bayesian behavioral) libraries. Ships with copy-pasteable templates in [`references/`](./skills/cogneuro-project/references/): `Subject` skeleton, `CLAUDE.md` template, conda envs, CLI script, orchestrator, and worked braincoder/bauer fit examples. |
| [`snakemake`](./skills/snakemake/) | Practical Snakemake-on-SLURM knowledge — driver placement (in `sbatch`, never on the login node), rule-output conventions for per-wildcard outputs, monitoring via the SLURM `--comment` field, recovery from crashed drivers (`--rerun-incomplete`), and `rerun-triggers: input` to stop forward-cascade reruns. Pairs with [`sciencecluster`](./skills/sciencecluster/). |

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
