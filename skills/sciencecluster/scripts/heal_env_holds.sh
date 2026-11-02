#!/bin/bash
# Release your SLURM tasks held with "user env retrieval failed requeued held",
# after excluding the node(s) they failed on, in small waves.
#
#   heal_env_holds.sh            # fix + release
#   heal_env_holds.sh --dry-run  # only report
#
# This is a safety net, not the fix. The hold only happens to jobs submitted
# with an --export LIST (--export=VAR=x, --export=ALL,VAR=x, --export=NONE):
# sbatch then sets SLURM_GET_USER_ENV=1 and slurmd runs `su - $USER` on the
# node before launch; on some nodes that fails within seconds. Submit with
# `VAR=x sbatch ...` (default --export=ALL) and the hold cannot occur.
# See SKILL.md, section "user env retrieval failed requeued held".
#
# Safe to run any time (login node or scrontab): it only touches held tasks
# with that reason. Every node with >= BAD_MIN env-launch requeues of your
# jobs in the last LOOKBACK, plus the nodes each task itself failed on, is
# appended to the task's ExcNodeList (existing exclusions kept) before release.
# scrontab jobs (empty SubmitLine) are ignored: they show REQUEUED after every
# normal cron cycle. Bad nodes also go to ~/.slurm_bad_nodes.
set -uo pipefail
DRY=0
[[ "${1:-}" == "-n" || "${1:-}" == "--dry-run" ]] && DRY=1
WAVE=${WAVE:-25}         # tasks released per wave
PAUSE=${PAUSE:-20}       # seconds between waves
BAD_MIN=${BAD_MIN:-2}    # requeues on a node before it counts as bad
LOOKBACK=${LOOKBACK:-now-1days}

log() { echo "[$(date '+%F %T')] $*"; }
expand() { [[ -z "$1" || "$1" == "(null)" ]] || scontrol show hostnames "$1"; }

mapfile -t held < <(squeue --me -h -t PD -r -o '%i|%r' \
    | awk -F'|' 'tolower($2) ~ /env.retrieval/ {print $1}')
if (( ${#held[@]} == 0 )); then
    log "no env-retrieval holds"
    exit 0
fi
log "${#held[@]} env-retrieval held task(s)"

# nodes with repeated launch failures for this user
# (SubmitLine last: it can contain '|'; empty SubmitLine = scrontab cron cycle)
mapfile -t bad < <(sacct -u "$USER" -S "$LOOKBACK" -D -X -n -P -o State,NodeList,SubmitLine \
    | awk -F'|' '$1 ~ /REQUEUED|NODE_FAIL|LAUNCH_FAILED/ && $2 != "None assigned" && $3 != "" {print $2}' \
    | while read -r nl; do expand "$nl"; done \
    | sort | uniq -c | awk -v m="$BAD_MIN" '$1 >= m {print $2}')
log "bad nodes (>= $BAD_MIN requeues since $LOOKBACK): ${bad[*]:-none}"
if (( ${#bad[@]} )) && (( ! DRY )); then
    { [[ -f ~/.slurm_bad_nodes ]] && tr ',' '\n' < ~/.slurm_bad_nodes; printf '%s\n' "${bad[@]}"; } \
        | sort -u | grep . | paste -sd, - > ~/.slurm_bad_nodes.tmp && mv ~/.slurm_bad_nodes.tmp ~/.slurm_bad_nodes
fi

ready=()
for id in "${held[@]}"; do
    own=$(sacct -j "$id" -D -X -n -P -o State,NodeList \
        | awk -F'|' '$1 ~ /REQUEUED|NODE_FAIL|LAUNCH_FAILED/ {print $2}')
    exc=$(scontrol show job "$id" | grep -o 'ExcNodeList=[^ ]*' | cut -d= -f2)
    new=$({ expand "$exc"; for n in $own; do expand "$n"; done; printf '%s\n' "${bad[@]}"; } \
        | grep . | sort -u | paste -sd, -)
    log "$id: exclude ${new:-<none>}"
    if (( ! DRY )); then
        [[ -n "$new" ]] && scontrol update JobId="$id" ExcNodeList="$new"
    fi
    ready+=("$id")
done
(( DRY )) && { log "dry run: nothing released"; exit 0; }

for ((i = 0; i < ${#ready[@]}; i += WAVE)); do
    wave=("${ready[@]:i:WAVE}")
    scontrol release "$(IFS=,; echo "${wave[*]}")"
    log "released ${#wave[@]} (wave $((i / WAVE + 1)))"
    (( i + WAVE < ${#ready[@]} )) || break
    sleep "$PAUSE"
    again=$(squeue --me -h -t PD -r -o '%i|%r' | awk -F'|' 'tolower($2) ~ /env.retrieval/' \
        | grep -cFf <(printf '%s|\n' "${wave[@]}") || true)
    if (( again * 2 > ${#wave[@]} )); then
        log "STOP: $again of the last wave were held again on other nodes. Resubmit without an --export list (VAR=x sbatch ...)."
        exit 1
    fi
done
log "done"
