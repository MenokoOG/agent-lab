"""m5: a small workflow engine. then, parallel, when, suspend, resume, spans.

A step is a function: state dict in, dict of updates out, or Suspend to wait for a human.
State stays JSON-serializable so a suspended run survives a process restart.
"""
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Union

Step = Callable[[dict], Union[dict, "Suspend"]]


@dataclass
class Suspend:
    reason: str


@dataclass
class Span:
    id: int
    parent: Optional[int]
    name: str
    start: float
    end: float = 0.0
    status: str = "ok"


class Trace:
    def __init__(self) -> None:
        self.spans: List[Span] = []
        self._lock = threading.Lock()

    def open(self, name: str, parent: Optional[int]) -> Span:
        with self._lock:
            span = Span(len(self.spans), parent, name, time.perf_counter())
            self.spans.append(span)
        return span

    def close(self, span: Span, status: str = "ok") -> None:
        span.end, span.status = time.perf_counter(), status

    def tree(self) -> List[str]:
        lines: List[str] = []

        def walk(parent, depth):
            for s in self.spans:
                if s.parent == parent:
                    lines.append(f"{'  ' * depth}{s.name}  {(s.end - s.start) * 1000:.1f} ms  {s.status}")
                    walk(s.id, depth + 1)
        walk(None, 0)
        return lines


@dataclass
class Run:
    run_id: str
    status: str  # "done" or "suspended"
    state: dict
    trace: Trace
    reason: str = ""


class Flow:
    def __init__(self, name: str, store: Path = Path("runs")) -> None:
        self.name, self.store = name, Path(store)
        self.nodes: List[tuple] = []

    def then(self, fn: Step) -> "Flow":
        self.nodes.append(("then", fn))
        return self

    def parallel(self, *fns: Step) -> "Flow":
        self.nodes.append(("parallel", fns))
        return self

    def when(self, cond: Callable[[dict], bool], fn: Step) -> "Flow":
        self.nodes.append(("when", cond, fn))
        return self

    def run(self, state: dict, run_id: Optional[str] = None) -> Run:
        return self._go(0, dict(state), run_id or uuid.uuid4().hex[:8])

    def resume(self, run_id: str, human_input: dict) -> Run:
        path = self.store / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"no suspended run {run_id} in {self.store}")
        saved = json.loads(path.read_text())
        run = self._go(saved["next"], {**saved["state"], **human_input}, run_id)
        if run.status == "done":
            path.unlink()  # a finished run can't be resumed twice
        return run

    def _call(self, fn: Step, state: dict, trace: Trace, parent: int):
        span = trace.open(fn.__name__, parent)
        try:
            out = fn(dict(state))
        except Exception as e:
            trace.close(span, f"error: {e}")
            raise
        trace.close(span)
        return out

    def _go(self, start: int, state: dict, run_id: str) -> Run:
        trace = Trace()
        root = trace.open(self.name, None)
        for i in range(start, len(self.nodes)):
            node = self.nodes[i]
            if node[0] == "then":
                out = self._call(node[1], state, trace, root.id)
            elif node[0] == "parallel":
                group = trace.open("parallel", root.id)
                with ThreadPoolExecutor() as pool:
                    outs = list(pool.map(lambda f: self._call(f, state, trace, group.id), node[1]))
                trace.close(group)
                if any(isinstance(o, Suspend) for o in outs):
                    raise TypeError("a parallel step cannot suspend")
                out = {k: v for o in outs for k, v in o.items()}
            else:
                _, cond, fn = node
                out = self._call(fn, state, trace, root.id) if cond(state) else {}
            if isinstance(out, Suspend):
                self.store.mkdir(parents=True, exist_ok=True)
                (self.store / f"{run_id}.json").write_text(json.dumps({"next": i + 1, "state": state}))
                trace.close(root, "suspended")
                return Run(run_id, "suspended", state, trace, out.reason)
            state.update(out)
        trace.close(root)
        return Run(run_id, "done", state, trace)
