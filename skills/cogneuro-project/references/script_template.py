"""<one-line description of what this script does>

Examples
--------
Single subject, local:
    python <package>/<stage>/<script>.py 1 --model 4

Cluster array job (typically called from slurm_jobs/<script>.sh):
    python <package>/<stage>/<script>.py 1 \\
        --bids_folder /shares/zne.uzh/gdehol/ds-<project> \\
        --model 4 --smoothed
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main(
    subject: int,
    bids_folder: str = '/data/ds-<project>',
    model: int = 4,
    smoothed: bool = False,
) -> None:
    # Echo resolved config so SLURM logs are searchable + typos surface fast.
    print(f'[<script>] subject={subject} model={model} '
          f'smoothed={smoothed} bids_folder={bids_folder}', flush=True)

    # Heavy imports inside main() — keeps `python -c "import <package>"` fast
    # and avoids GPU init during argparse error paths.
    from <package>.utils.data import Subject

    sub = Subject(subject, bids_folder=bids_folder)

    # --- analysis ---
    # data = sub.get_single_trial_estimates(session=1, smoothed=smoothed)
    # ...
    # sub._write_volume(result, masker, out_path)  # dtype-safe write


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('subject', type=int,
                        help='subject number (int; zero-padded internally)')
    parser.add_argument('--bids_folder',
                        default='/data/ds-<project>',
                        help='BIDS root (local default; SLURM overrides)')
    parser.add_argument('--model', type=int, default=4,
                        help='model label; see CLAUDE.md model table')
    parser.add_argument('--smoothed', action='store_true',
                        help='use spatially smoothed input BOLD')
    args = parser.parse_args()

    main(
        subject=args.subject,
        bids_folder=args.bids_folder,
        model=args.model,
        smoothed=args.smoothed,
    )
