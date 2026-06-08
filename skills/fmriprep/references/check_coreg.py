"""QA: overlay every space-T1w boldref on the T1w for each subject + run.

Batch, non-interactive. Produces one PDF per subject under
derivatives/qa/coreg/. Each page shows the preprocessed T1w with boldref
edges overlaid (nilearn's add_edges) — the canonical bbregister-style
coregistration check. This is the more reliable QA than the fmriprep HTML
flicker (see SKILL.md "HTML report rendering").

Lives at <package>/visualize/check_coreg.py. Run after fmriprep +
sync_fmriprep.sh has pulled outputs locally:

    python -m <package>.visualize.check_coreg
    python -m <package>.visualize.check_coreg --subjects 07 08 09 10

Open the resulting PDFs in Preview to flip through quickly. For the
interactive (fsleyes) version, see inspect_coreg_fsleyes.py.
"""

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # PDF writer (no display needed)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from nilearn import plotting

from <package>.utils.data import BIDS_FOLDER

DEFAULT_DERIV = Path(BIDS_FOLDER) / "derivatives" / "fmriprep"
DEFAULT_OUT = Path(BIDS_FOLDER) / "derivatives" / "qa" / "coreg"
RUN_RE = re.compile(r"(ses-\d+)_task-\w+?_(run-\d+)")


def find_t1w(sub_dir: Path) -> Path | None:
    """Pick the first available ses-*/anat preproc T1w (multi-session subjects
    typically have it under ses-1 only)."""
    for cand in sorted(sub_dir.glob("ses-*/anat/*desc-preproc_T1w.nii.gz")):
        return cand
    return None


def find_boldrefs(sub_dir: Path) -> list[Path]:
    return sorted(sub_dir.glob("ses-*/func/*_space-T1w_boldref.nii.gz"))


def plot_one(t1w: Path, boldref: Path, sub: str, label: str):
    fig = plt.figure(figsize=(14, 4.5))
    display = plotting.plot_anat(
        str(t1w),
        display_mode="ortho",
        title=f"{sub}  {label}",
        figure=fig,
        cut_coords=(0, 0, 0),
        draw_cross=False,
    )
    display.add_edges(str(boldref))
    return fig, display


def run(deriv: Path, out_dir: Path, subjects: list[str] | None):
    sub_dirs = sorted(
        p for p in deriv.glob("sub-*") if p.is_dir() and not p.name.startswith("sub-pil")
    )
    if subjects:
        wanted = {f"sub-{s.lstrip('sub-').lstrip('-')}" for s in subjects}
        sub_dirs = [p for p in sub_dirs if p.name in wanted]

    if not sub_dirs:
        print("No matching subjects found under", deriv)
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    for sub_dir in sub_dirs:
        sub = sub_dir.name
        t1w = find_t1w(sub_dir)
        if t1w is None:
            print(f"{sub}: no preproc T1w found — skipping")
            continue
        boldrefs = find_boldrefs(sub_dir)
        if not boldrefs:
            print(f"{sub}: no space-T1w boldrefs — skipping")
            continue

        pdf_path = out_dir / f"{sub}_coreg_check.pdf"
        with PdfPages(pdf_path) as pdf:
            for br in boldrefs:
                m = RUN_RE.search(br.name)
                label = f"{m.group(1)} {m.group(2)}" if m else br.name
                fig, _ = plot_one(t1w, br, sub, label)
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)
        print(f"{sub}: wrote {pdf_path}  ({len(boldrefs)} runs)")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--deriv",
        default=str(DEFAULT_DERIV),
        help="fmriprep derivatives directory (default: %(default)s)",
    )
    p.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="output directory for PDFs (default: %(default)s)",
    )
    p.add_argument(
        "--subjects",
        nargs="+",
        help="restrict to specific subject labels (e.g. 07 08); default: all study subjects",
    )
    args = p.parse_args()
    run(Path(args.deriv), Path(args.out), args.subjects)


if __name__ == "__main__":
    main()
