"""Interactive coreg QA: loop fsleyes over (subject, session), one run per session.

Opens fsleyes for one (T1w, space-T1w_boldref) pair at a time. Close the
window to advance to the next. Ctrl-C to bail out. By default uses the
lowest run number per session — pass --run to override.

The most reliable visual QA of BOLD<->T1w coregistration: inspect the BOLD
ribbon against cortex directly, rather than trusting the fmriprep HTML
flicker (see SKILL.md "HTML report rendering"). For a batch PDF version,
see check_coreg.py.

Lives at <package>/visualize/inspect_coreg_fsleyes.py.

Usage:
    python -m <package>.visualize.inspect_coreg_fsleyes
    python -m <package>.visualize.inspect_coreg_fsleyes --subjects 07 09
    python -m <package>.visualize.inspect_coreg_fsleyes --subjects 07 --run 3
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from <package>.utils.data import BIDS_FOLDER

DEFAULT_DERIV = Path(BIDS_FOLDER) / "derivatives" / "fmriprep"
PARSE_RE = re.compile(r"sub-(?P<sub>[A-Za-z0-9]+)_ses-(?P<ses>\d+)_task-\w+?_run-(?P<run>\d+)")


def find_t1w(sub_dir: Path) -> Path | None:
    for cand in sorted(sub_dir.glob("ses-*/anat/*desc-preproc_T1w.nii.gz")):
        return cand
    return None


def find_boldrefs(sub_dir: Path) -> list[tuple[int, int, Path]]:
    out = []
    for br in sorted(sub_dir.glob("ses-*/func/*_space-T1w_boldref.nii.gz")):
        m = PARSE_RE.search(br.name)
        if not m:
            continue
        out.append((int(m["ses"]), int(m["run"]), br))
    return out


def run(deriv: Path, subjects: list[str] | None, run_override: int | None):
    if not shutil.which("fsleyes"):
        print(
            "fsleyes not on PATH. Activate your env first (e.g. `conda activate "
            "<package>`) or install fsleyes.",
            file=sys.stderr,
        )
        sys.exit(1)

    sub_dirs = sorted(
        p for p in deriv.glob("sub-*") if p.is_dir() and not p.name.startswith("sub-pil")
    )
    if subjects:
        wanted = {f"sub-{s.lstrip('sub-').lstrip('-')}" for s in subjects}
        sub_dirs = [p for p in sub_dirs if p.name in wanted]
    if not sub_dirs:
        print("No matching subjects under", deriv)
        return

    for sub_dir in sub_dirs:
        sub = sub_dir.name
        t1w = find_t1w(sub_dir)
        if t1w is None:
            print(f"{sub}: no preproc T1w — skipping")
            continue
        boldrefs = find_boldrefs(sub_dir)
        if not boldrefs:
            print(f"{sub}: no boldrefs — skipping")
            continue

        # One run per session — by default the lowest run number; override with --run
        by_session: dict[int, tuple[int, Path]] = {}
        for ses, run_i, br in boldrefs:
            if run_override is not None and run_i != run_override:
                continue
            if ses not in by_session or run_i < by_session[ses][0]:
                by_session[ses] = (run_i, br)

        for ses in sorted(by_session):
            run_i, boldref = by_session[ses]
            label = f"{sub} ses-{ses} run-{run_i}"
            print(f"opening fsleyes for {label}  (close window to advance, Ctrl-C to quit)")
            cmd = [
                "fsleyes",
                str(t1w),
                str(boldref),
                "--cmap", "hot",
                "--alpha", "40",
            ]
            try:
                subprocess.run(cmd, check=False)
            except KeyboardInterrupt:
                print("\nBye.")
                return


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--deriv", default=str(DEFAULT_DERIV))
    p.add_argument("--subjects", nargs="+", help="restrict to these subject labels (e.g. 07 09)")
    p.add_argument("--run", type=int, help="use this specific run number (default: lowest available)")
    args = p.parse_args()
    run(Path(args.deriv), args.subjects, args.run)


if __name__ == "__main__":
    main()
