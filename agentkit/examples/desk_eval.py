"""Eval suite and CI gate for the support desk.

    python examples/desk_eval.py --dry-run                   # fake model, compares with baseline.dryrun.json
    python examples/desk_eval.py --save-baseline             # real run (spends tokens), writes baseline.json
    python examples/desk_eval.py                             # real run, gate against baseline.json
Exit code: 0 ok, 1 regression, 2 no baseline yet.
"""
import argparse
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentkit import llm  # noqa: E402
from agentkit.evals import Case, gate, judge, run_suite, save_baseline, summarize  # noqa: E402
from examples.support_desk import build_flow, handle  # noqa: E402

HERE = Path(__file__).resolve().parent

CASES: List[Case] = [
    Case("d01", "What is the status of order 1001?", "shipped", "orders", "order"),
    Case("d02", "Where is my order 1002?", "processing", "orders", "order"),
    Case("d03", "Order 1003, was it delivered?", "delivered", "orders", "order"),
    Case("d04", "How long do refunds take to reach my card?", "5 business days", "policy", "policy"),
    Case("d05", "Can I still return something after three weeks?", "30 days", "policy", "policy"),
    Case("d06", "How long does express shipping take?", "1 to 2 business days", "policy", "policy"),
    Case("d07", "My password reset link stopped working", "30 minutes", "policy", "policy"),
    Case("d08", "Order 1002 shows the wrong lamp, what does it say?", "desk lamp", "orders", "order"),
]


def desk_agent(use_mcp: bool, tier: str = "pro"):
    """question -> (reply, [specialist, *tools]). Auto-approves, since the suite tests the answer."""
    def agent(question: str) -> Tuple[str, List[str]]:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run = handle(question, "eval", tier, use_mcp, root)
            if run.status == "suspended":
                run = build_flow(use_mcp, root).resume(run.run_id, {"approved": "yes"})
            return run.state.get("reply") or "", [run.state.get("specialist", "")] + run.state.get("tools_used", [])
    return agent


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--save-baseline", action="store_true")
    ap.add_argument("--mcp", action="store_true", help="call tools over MCP (slower: a process per call)")
    args = ap.parse_args(argv)
    if args.dry_run:
        from examples.fake_model import desk_fake
        llm.FAKE = desk_fake
    results = run_suite(desk_agent(args.mcp), CASES, judge)
    s = summarize(results)
    print(f"accuracy {s['accuracy']:.0%}  route accuracy {s['route_accuracy']:.0%}  "
          f"modes {s['failure_modes'] or 'none'}")
    for r in results:
        if not r["passed"]:
            print(f"  FAIL {r['id']} {r['mode']}: {r['answer'][:90]}")
    baseline = HERE / ("baseline.dryrun.json" if args.dry_run else "baseline.json")
    if args.save_baseline:
        save_baseline(s, baseline, "dry run, plumbing only" if args.dry_run else "real model run")
        print(f"saved {baseline.name}")
        return 0
    code, msg = gate(s, baseline)
    print(msg)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
