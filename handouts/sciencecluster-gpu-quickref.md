# Quick reference: GPU jobs on UZH sciencecluster (TensorFlow / braincoder)

One-pager for your Claude context (drop next to `CLAUDE.md`). Symptom this
solves: **a SLURM job lands on a GPU node but silently computes on CPU** —
braincoder/TF decoding runs ~25× slower than expected, then hits walltime.

## The four causes (all produce the identical silent-CPU symptom)

1. **No `--gres=gpu:1`.** There is no GPU partition on sciencecluster;
   without `--gres`, SLURM's cgroup hides every GPU on the node. This is
   the only way to get a GPU.
2. **Non-CUDA env.** Plain `pip install tensorflow` falls back to CPU with
   no error. Use `tensorflow[and-cuda]` / `jax[cuda12]` — these wheels
   bundle their own CUDA runtime; no `module load cuda` needed, and no GPU
   node needed at env-build time.
3. **cuInit race.** Several array tasks starting simultaneously on the same
   8-GPU node (V100/A100/H100 boxes) deadlock the NVIDIA driver's init; TF
   falls back to CPU even though the GPU is allocated. Random sleep stagger
   does NOT reliably fix it. Fix: a per-node `flock`ed warm-up before the
   real work (first job on the node initializes CUDA under a node-local
   lock; the rest find a warm driver):

   ```bash
   LOCK="/tmp/cuinit_warm_$(hostname -s).flock"
   ( flock -w 60 -x 200 || exit 0
     python -c "import tensorflow as tf; tf.config.list_physical_devices('GPU')"
   ) 200>"$LOCK"
   ```

   (L4 nodes have 1 GPU/node and can't race — `--constraint=L4` is an
   alternative fix.)
4. **CUDA 11 env on H100/H200.** Those GPUs (sm_90) need CUDA 12; an older
   `cudatoolkit=11.x` env can't initialize them. Either exclude them with
   `#SBATCH --constraint="L4|V100|A100"` or rebuild the env on current
   wheels. Check what you have:
   `python -c "import tensorflow.sysconfig as s; print(s.get_build_info()['cuda_version'])"`

## Two lines that save hours

**Fail fast** — put this after env activation in every GPU job, so a
misconfigured job dies in 20 s instead of burning 6 h on CPU:

```bash
python -c "import sys, tensorflow as tf; gpus = tf.config.list_physical_devices('GPU'); print('GPUs:', gpus, flush=True); sys.exit(0 if gpus else 'FATAL: no GPU visible')"
```

**Pin the Keras backend** for braincoder on Keras 3:

```bash
export KERAS_BACKEND=tensorflow
```

Also: launch python as `exec .../envs/<env>/bin/python -u script.py` with
`PYTHONUNBUFFERED=1`. Never `conda run` (it buffers all stdout until exit,
so you can't tell a working job from a hung one) and no `set -u` in the job
script (conda activation aborts under it).

## Did a finished job actually use the GPU?

- `grep 'GPUs:' <log>` (with the fail-fast line above) answers directly.
- `sacct -j <id> --format=JobID,Elapsed,State` — CPU-fallback tasks run
  ~25× longer than their GPU siblings in the same array.
- Live: `srun --jobid=<id> --overlap nvidia-smi` — 0 MiB GPU memory while
  the job computes means CPU.

## The full skill

This page is the extract; the complete operational skill (partitions, QoS,
walltime strategy, exit-code diagnosis, array throttling / held tasks,
apptainer, env building, templates) is public:

**<https://github.com/Gilles86/gilles-claude-skills>** — install with
`git clone` + `./install.sh`, or copy `skills/sciencecluster/` into
`~/.claude/skills/`. Claude Code then loads it automatically for any
cluster/SLURM work; the GPU specifics live in its
`references/gpu_jobs.md`. A longer prose version of this handout is at
`handouts/sciencecluster-gpu-tensorflow.md`.
