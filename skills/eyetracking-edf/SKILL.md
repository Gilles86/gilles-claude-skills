---
name: eyetracking-edf
description: Parse SR Research EyeLink .edf files (events + raw gaze samples) via edf2asc, on a SLURM cluster. Covers the Linux-only binary constraint, the two-pass ASCII conversion pattern (msg vs. samples), phase/trial-onset parsing from exptools2-style MSG lines, and — the part everyone gets wrong — deriving pixel-to-degrees conversion from the per-run experiment-settings log rather than hardcoding screen geometry. Use whenever asked to extract gaze position, fixations, dispersion, saccades, or trajectories from raw EyeLink data, or to convert .edf to .asc.
---

# EyeLink EDF analysis on a SLURM cluster

Short on purpose: one hard constraint, one conversion pattern, one
frequently-wrong conversion step, and a worked skeleton. Project-specific
paths (which repo has the binary, which BIDS layout, which columns the
events.tsv has) belong in the calling project's own scripts — this is the
generic method.

## The hard constraint: `edf2asc` is Linux-only

SR Research ships `edf2asc` as a Linux x86-64 ELF binary. There is no
macOS build available in this ecosystem. **Any .edf parsing step must run
on the cluster (or another Linux box), never locally on macOS** — plan
the pipeline as "cluster extracts + aggregates → small TSV → rsync back
→ everything downstream runs locally", same split as any other
many-small-files aggregation job (see the `sciencecluster` skill).

Check for an existing copy before assuming you need to obtain one — it
tends to already be checked into whichever eyetracking-using repo you
worked on last (e.g. `<repo>/edf2asc`, ~100 KB, not from apt/conda).
Reuse it via an absolute path rather than re-vendoring a new copy per
project.

## Two-pass ASCII conversion

Convert each `.edf` **twice** — once for events, once for samples — then
parse both as plain text. Doing it in one pass produces an interleaved
file that's harder to parse reliably.

```bash
edf2asc -t -y -z -v -e in.edf out_msg.asc   # -e: event data only (MSG/START/END lines)
edf2asc -t -y -z -v -s in.edf out_samp.asc  # -s: sample data only (raw x/y/pupil @ device Hz)
```

Flags: `-t` tab-delimited (not space — much easier to `split("\t")`),
`-y` overwrite without prompting (required for non-interactive batch
jobs), `-z` disable-and-autofix consistency checking (raw files
routinely have minor internal inconsistencies; without `-z` conversion
can abort), `-v` verbose warnings to stderr (cheap, useful when a file
silently produces zero trials).

## Parsing events: trial/phase onsets from MSG lines

If the task was built with **exptools2** (`Trial.log_phase_info`), every
phase transition is logged as a message with a predictable format:

```
MSG	<timestamp>	start_type-stim_trial-<trial_nr>_phase-<phase_nr>
```

```python
import re
MSG_RE = re.compile(r"start_type-stim_trial-(-?\d+)_phase-(\d+)")

def parse_phase_onsets(msg_asc_path):
    onsets = {}  # (trial_nr, phase) -> timestamp (int, device clock units)
    with open(msg_asc_path, errors="ignore") as f:
        for line in f:
            if not line.startswith("MSG"):
                continue
            m = MSG_RE.search(line)
            if not m:
                continue
            trial_nr, phase = int(m.group(1)), int(m.group(2))
            if trial_nr < 0:          # pre-run calibration probe trials
                continue
            onsets[(trial_nr, phase)] = int(line.split("\t")[1])
    return onsets
```

Map phase numbers to task semantics by reading the experiment's
`phase_names` (or equivalent) — don't guess; get it from the task code.
The window between two phase onsets (e.g. "response start" → "feedback
start") is usually the epoch of interest.

## Parsing samples

```python
import numpy as np

def parse_samples(samp_asc_path):
    """Returns (times, x, y) arrays. EyeLink '.' (missing/blink) -> NaN."""
    times, xs, ys = [], [], []
    with open(samp_asc_path, errors="ignore") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            t = parts[0].strip()
            if not t.lstrip("-").isdigit():   # skips header/footer junk lines
                continue
            times.append(int(t))
            for col, dst in ((1, xs), (2, ys)):
                v = parts[col].strip()
                dst.append(np.nan if v in (".", "") else float(v))
    return np.array(times), np.array(xs), np.array(ys)
```

## The step everyone gets wrong: pixel → degrees

Screen width/distance/resolution are **not constants** — they differ by
testing room, and can differ even between two runs on paper "the same"
setup (a monitor swap, a resolution change mid-study). Hardcoding a
`width_cm`/`distance_cm` from a lab wiki page or a settings template is a
standing source of silently-wrong visual angles.

**The only reliable source is the per-run experiment log**, if the task
software writes one (PsychoPy/exptools2 `_expsettings.yml`, or
equivalent). Read monitor width, distance, and window resolution from
the log file matching *that specific run*, not from a shared config:

```python
import yaml

def load_geometry(expsettings_path):
    with open(expsettings_path) as f:
        s = yaml.safe_load(f)
    width_cm    = float(s["monitor"]["width"])
    distance_cm = float(s["monitor"]["distance"])
    w_px, h_px  = s["window"]["size"]
    return width_cm, distance_cm, int(w_px), int(h_px)

def pix2deg(offset_px, width_cm, width_px, distance_cm):
    """Visual angle (deg) of a pixel offset from screen centre.
    Exact flat-screen formula (not the small-angle approximation) —
    matters once offsets get to be several degrees."""
    offset_cm = offset_px * (width_cm / width_px)
    return np.degrees(np.arctan(offset_cm / distance_cm))

# offset from screen centre, y flipped (EyeLink pixel y grows downward)
x_deg = pix2deg(xs - w_px / 2, width_cm, w_px, distance_cm)
y_deg = pix2deg(h_px / 2 - ys, width_cm, w_px, distance_cm)
```

If no per-run log exists, at minimum confirm geometry with whoever ran
the session rather than assuming a template — and say so explicitly in
the extraction script's docstring, so the next person doesn't trust a
number that was actually a guess.

## Putting it together: per-trial extraction skeleton

```python
def process_run(edf_path, tmp_dir, **trial_keys):
    msg_asc, samp_asc = convert(edf_path, tmp_dir)   # the two edf2asc calls above
    try:
        onsets = parse_phase_onsets(msg_asc)
        times, xs, ys = parse_samples(samp_asc)
        width_cm, distance_cm, w_px, h_px = load_geometry(
            edf_path.with_name(edf_path.stem + "_expsettings.yml"))
        x_deg = pix2deg(xs - w_px / 2, width_cm, w_px, distance_cm)
        y_deg = pix2deg(h_px / 2 - ys, width_cm, w_px, distance_cm)

        rows = []
        for trial_nr in sorted({t for t, p in onsets if p == PHASE_OF_INTEREST}):
            t0 = onsets.get((trial_nr, PHASE_START))
            t1 = onsets.get((trial_nr, PHASE_END))
            if t0 is None or t1 is None or t1 <= t0:
                continue
            mask = (times >= t0) & (times < t1)
            # ... reduce mask'd x_deg/y_deg to whatever you need per trial
            # (scalar dispersion, resampled trajectory, fixation clusters, ...)
        return rows
    finally:
        msg_asc.unlink(missing_ok=True)
        samp_asc.unlink(missing_ok=True)   # .asc files are large; don't accumulate them
```

Loop this over every `.edf` under the source tree, `pd.DataFrame(all_rows).to_csv(...)`,
submit as one `sbatch`/`srun` job (I/O-bound subprocess calls — 1-2 CPUs,
a few GB RAM is plenty even for hundreds of files), and rsync the
resulting TSV back for local analysis.

## Worked, complete examples

Two full, project-specific but readable extraction scripts (scalar
per-trial dispersion, and resampled per-trial trajectories) live in
`~/git/abstract_values/abstract_values/eyetracking/`:
`extract_gaze_dispersion.py` and `extract_gaze_trajectories.py`. The
latter is the more complete reference for the geometry-from-per-run-log
pattern above.
