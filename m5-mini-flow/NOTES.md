# m5 mini-flow notes

- No step makes more than one LLM call. `merge_flags` and `mark_priority` make none.
- Restart test (2026-11-25, fake model): `triage.py` suspended run `3f8cce7d`, the process exited, and `triage.py --resume 3f8cce7d yes` in a new process drafted the reply. State lives in `runs/<id>.json`.
- The span tree shows the parallel group and each check under it. With the fake model every step is under 1 ms, so the real timing lesson needs a live run.
- Gap I found: a resumed run isn't deleted, so the same id can resume twice. agentkit's `Flow.resume` deletes the file once the run finishes.
