# f1 langgraph notes

- 8 tests pass with `python -m unittest` (langgraph 1.2.24, langchain-anthropic 1.7.12).
- Pause and resume across processes, fake model, 2026-11-25: run paused as thread `f6733c60`, then `triage_graph.py --resume f6733c60 yes` from a new process printed `category=billing flags=['urgent', 'angry', 'refund'] priority=high`.
- Lines: my mini-flow is 200 (`flow.py` 122 + `triage.py` 78). The graph is 136 (`triage_graph.py`).
- What replaced what: `.parallel` became fan-out edges from `classify`; `.when` became a conditional edge; `Suspend` became `interrupt()`.
- What LangGraph does that mine doesn't: it checkpoints after every node into SQLite, so a crash mid-run resumes from the last finished node. Mine resumes only from a suspend.
