"""m8: context engineering. Compaction with a must-keep list, structured state, an error repair loop."""
import json
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Sequence, Tuple

from agentkit import llm


def est_tokens(messages: List[dict]) -> int:
    return sum(max(1, len(json.dumps(m["content"])) // 4) for m in messages)


def llm_summarize(old: List[dict]) -> str:
    text = "\n".join(f"{m['role']}: {m['content'] if isinstance(m['content'], str) else json.dumps(m['content'])}"
                     for m in old)
    return llm.ask("Summarize this conversation so work can continue. Keep names, numbers and open questions. "
                   f"Be short.\n\n{text}", model=llm.SMALL_MODEL, max_tokens=400)


def compact(messages: List[dict], threshold: int, keep_last: int = 4, must_keep: Sequence[str] = (),
            summarize: Callable[[List[dict]], str] = llm_summarize) -> List[dict]:
    """Under the threshold, return the messages untouched. Over it, replace all but the last keep_last
    with one summary. must_keep lines are copied verbatim, because a summary drops detail by design."""
    if est_tokens(messages) <= threshold or len(messages) <= keep_last:
        return messages
    old, recent = messages[:-keep_last], messages[-keep_last:]
    kept = "\n".join(f"- {d}" for d in must_keep) or "- none"
    note = f"Summary of earlier work:\n{summarize(old)}\n\nDecisions to keep verbatim:\n{kept}"
    while recent and recent[0]["role"] != "user":  # keep the list starting on a user turn
        recent = recent[1:]
    return [{"role": "user", "content": note}] + recent


PREFIXES = {"FACT:": "facts", "DECISION:": "decisions", "QUESTION:": "open_questions"}


@dataclass
class State:
    goal: str
    facts: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)

    def add(self, kind: str, item: str) -> None:
        bucket = getattr(self, kind)
        if item not in bucket:
            bucket.append(item)


def update_from_text(state: State, text: str) -> State:
    for line in text.splitlines():
        line = line.strip()
        for prefix, attr in PREFIXES.items():
            if line.startswith(prefix):
                state.add(attr, line[len(prefix):].strip())
    return state


def compile_state(state: State) -> str:
    def block(title, items):
        return f"{title}:\n" + ("\n".join(f"- {i}" for i in items) if items else "- none")
    return "\n\n".join([f"Goal: {state.goal}", block("Decisions", state.decisions),
                        block("Facts", state.facts), block("Open questions", state.open_questions)])


def run_py(code: str, timeout: int = 10) -> Tuple[int, str, str]:
    """A subprocess is not a sandbox. Use guards.run_sandboxed for model-written code you don't trust."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d, "main.py")
        path.write_text(code)
        try:
            p = subprocess.run([sys.executable, "-I", str(path)], capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return 1, "", "TimeoutError: script ran too long"
    return p.returncode, p.stdout, p.stderr


def error_signature(stderr: str) -> str:
    lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
    return lines[-1] if lines else "unknown error"


def repair_loop(task: str, ask: Callable[[str], str] = llm.ask, run: Callable = run_py,
                max_tries: int = 3) -> Tuple[str, Counter]:
    """Write code, run it, feed the error back, repeat. Returns (stdout, error counts)."""
    errors: Counter = Counter()
    code = ask(f"Write a Python script for: {task}\nReturn only code, no markdown fences.")
    for _ in range(max_tries):
        rc, out, err = run(code)
        if rc == 0:
            return out, errors
        errors[error_signature(err)] += 1
        code = ask(f"Task: {task}\n\nCode:\n{code}\n\nError:\n{err}\n\nReturn the fixed code only, no markdown fences.")
    raise RuntimeError(f"still failing after {max_tries} tries: {dict(errors)}")
