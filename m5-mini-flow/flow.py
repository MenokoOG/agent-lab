"""A tiny workflow engine: then, parallel, when, suspend, resume, spans.

A step is a function: state dict in, dict of updates out (or Suspend to wait for a human).
State must stay JSON-serializable so a suspended run can be saved to disk.
"""
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

RUNS = Path("runs")


@dataclass
class Suspend:
    reason: str


@dataclass
class Span:
    id: int
    parent: int
    name: str
    input: dict
    output: object = None
    start: float = 0.0
    end: float = 0.0


class Trace:
    def __init__(self):
        self.spans, self._lock = [], threading.Lock()

    def open(self, name, input, parent):
        with self._lock:
            span = Span(len(self.spans), parent, name, dict(input), start=time.perf_counter())
            self.spans.append(span)
        return span

    def close(self, span, output):
        span.output, span.end = output, time.perf_counter()

    def print_tree(self, out=print):
        def walk(parent, depth):
            for s in self.spans:
                if s.parent == parent:
                    out(f"{'  ' * depth}{s.name}  {(s.end - s.start) * 1000:.1f} ms")
                    walk(s.id, depth + 1)
        walk(None, 0)


@dataclass
class Run:
    run_id: str
    status: str  # "done" or "suspended"
    state: dict
    trace: Trace
    reason: str = ""


class Flow:
    def __init__(self, name):
        self.name, self.nodes = name, []

    def then(self, fn):
        self.nodes.append(("then", fn))
        return self

    def parallel(self, *fns):
        self.nodes.append(("parallel", fns))
        return self

    def when(self, cond, fn):
        self.nodes.append(("when", cond, fn))
        return self

    def run(self, state, run_id=None):
        return self._go(0, dict(state), run_id or uuid.uuid4().hex[:8])

    def resume(self, run_id, human_input):
        saved = json.loads((RUNS / f"{run_id}.json").read_text())
        return self._go(saved["next"], {**saved["state"], **human_input}, run_id)

    def _call(self, fn, state, trace, parent):
        span = trace.open(fn.__name__, state, parent)
        try:
            out = fn(dict(state))
        except Exception as e:
            trace.close(span, f"error: {e}")
            raise
        trace.close(span, out)
        return out

    def _go(self, start, state, run_id):
        trace = Trace()
        root = trace.open(self.name, state, None)
        for i in range(start, len(self.nodes)):
            node = self.nodes[i]
            if node[0] == "then":
                out = self._call(node[1], state, trace, root.id)
            elif node[0] == "parallel":
                group = trace.open("parallel", state, root.id)
                with ThreadPoolExecutor() as pool:
                    outs = list(pool.map(lambda f: self._call(f, state, trace, group.id), node[1]))
                trace.close(group, outs)
                if any(isinstance(o, Suspend) for o in outs):
                    raise TypeError("a parallel step cannot suspend")
                out = {k: v for o in outs for k, v in o.items()}  # merge
            else:
                _, cond, fn = node
                out = self._call(fn, state, trace, root.id) if cond(state) else {}
            if isinstance(out, Suspend):
                RUNS.mkdir(exist_ok=True)
                (RUNS / f"{run_id}.json").write_text(json.dumps({"next": i + 1, "state": state}))
                trace.close(root, "suspended")
                return Run(run_id, "suspended", state, trace, out.reason)
            state.update(out)
        trace.close(root, state)
        return Run(run_id, "done", state, trace)
