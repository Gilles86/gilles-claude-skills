# Audit punchlist — house-style gaps to clean up

Improvements that were absent or partial across audited projects
(neural_priors, abstract_values, retinonumeral, retsupp). When
touching a project that's missing one of these, fix it.

1. **`tests/test_data.py`** — construct `Subject(1)` and
   `Subject(quirky_id)`, exercise every `get_*` method, round-trip a
   64-distinct-value array through `_write_volume` to catch the uint8
   quantization bug. Mock to a tmpdir; doesn't need real BIDS. See
   [test_data.py](test_data.py).

2. **Ad-hoc one-off scripts in `scripts/one_off/<topic>/`**, not at
   repo root. abstract_values has `fix_sub06_t2mgz.sh`,
   `run_decoding_pil01.sh`, `fix_and_move_bids.py` at the top — a mess
   that's hard to navigate later.

3. **`scripts/ingest_new_session.sh`** orchestrator — chains
   fmriprep → glmsingle → modeling → decoding via
   `--dependency=afterok` per-subject (failure isolation). See
   [ingest_new_session.sh](ingest_new_session.sh).

4. **`Makefile` or `tasks.py`** for the 3–4 most common commands
   (env build, BIDS smoke test, one-subject fit). Useful when you
   come back to a project after months and don't remember the entry
   points.

5. **A `.gitignore` that excludes `build/` and `*.egg-info/`** —
   neural_priors has `build/` committed. Use [gitignore](gitignore).
