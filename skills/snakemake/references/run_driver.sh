#!/bin/bash
#SBATCH --job-name=<project>_snake_driver
#SBATCH --account=<account>
#SBATCH --partition=standard           # NOT lowprio — driver is a long-lived CPU job
#SBATCH --qos=normal                   # 1-day cap; re-submit if it runs out (Snakemake resumes)
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=1-00:00:00
#SBATCH --output=$HOME/logs/snake_driver_%j.log
#
# Snakemake driver for the <project> cluster pipeline.
# Runs as its own SLURM job so the long-running driver process isn't subject
# to login-node ulimits (see snakemake skill: "driver placement").
#
# Usage:
#   ssh <cluster> 'cd ~/git/<project> && \
#       sbatch <project>/snakemake/run_driver.sh'
#
# Re-submitting the same script after `scancel` resumes where the previous
# driver left off — see the unlock / --rerun-incomplete dance below.

set -eo pipefail

cd "$HOME/git/<project>"

source "$HOME/data/miniforge3/etc/profile.d/conda.sh"
conda activate <project>           # or <project>_snake — env with snakemake + executor plugin

# ── pre-flight cleanup ───────────────────────────────────────────────────────
# Snakemake leaves TWO kinds of stale state when a driver is scancel'd:
#   1. .snakemake/lock           → LockException on next start
#   2. incomplete-output metadata → IncompleteFilesException on next start
# Clear both so re-submission "just works". Both are idempotent.

snakemake \
    --snakefile <project>/snakemake/Snakefile \
    --workflow-profile <project>/snakemake/profile \
    --configfile <project>/snakemake/config.yaml \
    --unlock || true                 # || true: --unlock returns nonzero when no lock exists

exec snakemake \
    --snakefile <project>/snakemake/Snakefile \
    --workflow-profile <project>/snakemake/profile \
    --configfile <project>/snakemake/config.yaml \
    --rerun-incomplete               # handles IncompleteFilesException
