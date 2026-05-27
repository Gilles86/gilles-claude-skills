#!/usr/bin/env bash
# Human-readable status for jobs in flight on the cluster.
#
# Snakemake-submitted jobs have:
#   - Name:    a UUID (per driver run, set by snakemake-executor-plugin-slurm)
#   - Comment: rule_<rule_name>_wildcards_<key=value,...>   (carries the meaning)
# Traditional sbatch jobs use Name for identity. This helper surfaces whichever
# is meaningful.
#
# Modes:
#   (default)        all of $USER's jobs
#   --snake          only this project's Snakemake jobs (auto-detected via
#                    most-recent driver log mentioning <project>)
#   --remote         already on cluster — skip the ssh hop
#
# Usage:
#   bash <project>/snakemake/status.sh
#   bash <project>/snakemake/status.sh --snake
#   bash <project>/snakemake/status.sh --snake --remote

set -eo pipefail

PROJECT="<project>"                          # the string that appears in your driver log

SNAKE_ONLY=0
ON_CLUSTER=0
for arg in "$@"; do
    case "$arg" in
        --snake|--snakemake) SNAKE_ONLY=1 ;;
        --remote)            ON_CLUSTER=1 ;;
    esac
done

run() {
    if [[ "$ON_CLUSTER" -eq 1 ]]; then bash -c "$1"; else ssh <cluster> "$1"; fi
}

fmt='JobID:14,State:10,TimeUsed:10,Partition:10,Name:38,Comment:90'
raw=$(run "squeue -u \$USER -h -O '$fmt'")

if [[ "$SNAKE_ONLY" -eq 1 ]]; then
    uuid=$(run "ls -t ~/logs/snake_driver_*.log 2>/dev/null | \
                xargs grep -l '$PROJECT' 2>/dev/null | head -1 | \
                xargs grep -m1 'SLURM run ID:' 2>/dev/null | awk '{print \$NF}'")
    if [[ -z "$uuid" ]]; then
        echo "No active $PROJECT snakemake driver found." >&2
        exit 1
    fi
    echo "(filtering to driver run UUID: $uuid)"
    raw=$(echo "$raw" | grep -F "$uuid" || true)
    if [[ -z "$raw" ]]; then
        echo "Driver is running but no child jobs in queue yet (or all done)."
        exit 0
    fi
fi

echo "=== counts ==="
echo "$raw" | awk '{print $2}' | sort | uniq -c | sort -rn
echo

# Per-job table: for Snakemake jobs the Name is a UUID, so we surface the
# Comment (rule + wildcards) as the headline.
echo "$raw" | awk '
    BEGIN { printf "%-12s %-9s %-9s %-9s %-22s %s\n",
                   "JOBID","STATE","TIME","PART","NAME","DETAIL" }
    {
        jobid=$1; state=$2; t=$3; part=$4;
        name = $5
        detail = ""
        for (i=6; i<=NF; i++) detail = (detail ? detail " " : "") $i
        if (detail == "") detail = "(no comment)"
        if (length(name) > 22) name = substr(name, 1, 19) "…"
        printf "%-12s %-9s %-9s %-9s %-22s %s\n", jobid, state, t, part, name, detail
    }'
