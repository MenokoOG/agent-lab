"""m9: evals. A binary judge, a suite runner with failure modes, and a baseline gate for CI."""
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from agentkit import llm

JUDGE = """You grade an answer against a reference. Reply with exactly PASS or FAIL.
Criteria: {criteria}
Question: {q}
Reference: {ref}
Answer: {ans}"""

DEFAULT_CRITERIA = ("The answer states the same facts as the reference. Extra correct detail is fine. "
                    "Any wrong number, name or missing required step is a FAIL.")

Agent = Callable[[str], Tuple[str, List[str]]]  # question -> (answer, tools or route used)
Judge = Callable[[str, str, str], bool]


def judge(q: str, ref: str, ans: str, criteria: str = DEFAULT_CRITERIA) -> bool:
    """Binary beats a 1 to 10 score: models grade words better than numbers."""
    reply = llm.ask(JUDGE.format(criteria=criteria, q=q, ref=ref, ans=ans), max_tokens=5)
    return reply.strip().upper().startswith("PASS")


@dataclass
class Case:
    id: str
    question: str
    reference: str
    expected: str  # tool or route name that must appear in what the agent used
    tag: str = ""


def failure_mode(errored: bool, route_ok: bool) -> str:
    if errored:
        return "budget_or_error"
    return "wrong_answer" if route_ok else "wrong_route"


def run_suite(agent: Agent, cases: List[Case], judge_fn: Judge = judge) -> List[dict]:
    results = []
    for c in cases:
        start = time.perf_counter()
        errored, answer = False, ""
        used: List[str] = []
        try:
            answer, used = agent(c.question)
        except RuntimeError as e:  # step budget and surfaced tool errors land here
            errored, answer = True, f"[{e}]"
        route_ok = c.expected in used
        passed = (not errored) and route_ok and judge_fn(c.question, c.reference, answer)
        results.append({"id": c.id, "tag": c.tag, "passed": passed, "route_ok": route_ok,
                        "latency_s": round(time.perf_counter() - start, 3), "answer": answer,
                        "mode": None if passed else failure_mode(errored, route_ok)})
    return results


def summarize(results: List[dict]) -> Dict[str, object]:
    if not results:
        raise ValueError("no results to summarize")
    n = len(results)
    by_tag: Dict[str, List[bool]] = defaultdict(list)
    for r in results:
        by_tag[r["tag"]].append(r["passed"])
    return {"n": n,
            "accuracy": sum(r["passed"] for r in results) / n,
            "route_accuracy": sum(r["route_ok"] for r in results) / n,
            "failure_modes": dict(Counter(r["mode"] for r in results if r["mode"])),
            "accuracy_by_tag": {t: sum(v) / len(v) for t, v in by_tag.items()}}


def passes(accuracy: float, baseline: float, tolerance: float = 0.01) -> bool:
    return accuracy >= baseline - tolerance


def gate(summary: dict, baseline_path: Path, tolerance: float = 0.01) -> Tuple[int, str]:
    """Exit code and message. 0 ok, 1 regression, 2 no baseline yet."""
    if not baseline_path.exists():
        return 2, f"no baseline at {baseline_path}; save one from a known-good run first"
    baseline = json.loads(baseline_path.read_text())["accuracy"]
    if not passes(summary["accuracy"], baseline, tolerance):
        return 1, f"REGRESSION: accuracy {summary['accuracy']:.3f} below baseline {baseline:.3f}"
    return 0, f"ok: accuracy {summary['accuracy']:.3f} (baseline {baseline:.3f})"


def save_baseline(summary: dict, path: Path, note: Optional[str] = None) -> None:
    path.write_text(json.dumps({"accuracy": summary["accuracy"], "n": summary["n"], "note": note or ""}, indent=2))
