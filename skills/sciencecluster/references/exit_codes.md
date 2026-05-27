# Reading SLURM exit codes — the two "OOM"s aren't the same

**When to load:** a class of jobs is failing repeatedly and you're
running `sacct` to figure out why. Particularly useful when "the job
OOM'd" is ambiguous (host RAM vs GPU VRAM).

`sacct -X --format=JobID,State,ExitCode` is the first thing to look
at when a job class fails repeatedly.

## The three failure shapes to recognize

- **`State=OUT_OF_MEMORY`, `ExitCode=0:125`** — the kernel SIGKILL'd
  the process because the cgroup enforcing `--mem` exceeded its
  budget. **Host RAM** problem. Either bump `--mem`, reduce the
  workload (smaller batch / chunk), or check whether the job is
  silently running on CPU when it should be on GPU (CPU TF needs
  much more host RAM than GPU TF — the gradient tape moves from
  VRAM to DRAM).
- **`State=FAILED`, `ExitCode=1:0`** — Python raised and exited 1.
  Could be `tensorflow.python.framework.errors_impl.ResourceExhaustedError`
  (that's **GPU VRAM** OOM), an assertion, a NaN/Inf, an import
  error, etc. The traceback is in the log; read it.
- **`State=TIMEOUT`** — walltime hit. Bump `--time` if the job
  genuinely needs longer, or investigate whether it's running
  silently degraded (CPU fallback → 25× slower → can't finish in
  time).

## Don't conflate them

The colloquial "the job OOM'd" usually means `0:125` if it's host
RAM, `1:0 + ResourceExhaustedError` if it's GPU VRAM. They have
different fixes; don't conflate them.
