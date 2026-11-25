"""Run the golden set through an agent, judge each answer, tag failures, write results.

    python suite.py                   # real run (needs ANTHROPIC_API_KEY)
    python suite.py --save-baseline   # real run, then store the accuracy as baseline.json
    python suite.py --dry-run         # fake agent that echoes the reference, plumbing only
"""
import argparse
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))
from judge import judge  # noqa: E402

HERE = Path(__file__).parent


def load_golden(path=HERE / "golden.csv"):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def book_agent(question):
    """The agent under test: module 2's loop and tools. Returns (answer, tools called)."""
    import tools
    from loop import run_agent
    r = run_agent(question, tools.TOOLS, tools.HANDLERS,
                  system="You analyze a book corpus. Use the tools for counts and lists. Answer briefly.")
    return r.answer, r.tool_calls


def failure_mode(errored: bool, tool_ok: bool) -> str:
    if errored:
        return "budget_or_error"
    return "wrong_answer" if tool_ok else "wrong_tool"


def run_suite(agent, rows, judge_fn=judge) -> list:
    results = []
    for row in rows:
        start = time.perf_counter()
        errored, answer, called = False, "", []
        try:
            answer, called = agent(row["question"])
        except RuntimeError as e:
            errored, answer = True, f"[{e}]"
        latency = time.perf_counter() - start
        expected = set(row["expected_tools"].split("|"))
        tool_ok = bool(expected & set(called))
        passed = (not errored) and judge_fn(row["question"], row["reference"], answer)
        results.append({"id": row["id"], "tag": row["tag"], "question": row["question"], "answer": answer,
                        "passed": passed, "tool_ok": tool_ok, "latency_s": round(latency, 3),
                        "mode": None if passed else failure_mode(errored, tool_ok)})
    return results


def summarize(results) -> dict:
    n = len(results)
    by_tag = defaultdict(list)
    for r in results:
        by_tag[r["tag"]].append(r["passed"])
    return {"n": n,
            "accuracy": sum(r["passed"] for r in results) / n,
            "tool_accuracy": sum(r["tool_ok"] for r in results) / n,
            "avg_latency_s": sum(r["latency_s"] for r in results) / n,
            "failure_modes": dict(Counter(r["mode"] for r in results if r["mode"])),
            "accuracy_by_tag": {t: sum(v) / len(v) for t, v in by_tag.items()}}


def write_failures(results, path=HERE / "FAILURES.md"):
    lines = ["# Failures", "", "| id | tag | mode | question | got |", "| --- | --- | --- | --- | --- |"]
    for r in results:
        if not r["passed"]:
            got = r["answer"].replace("|", "/").replace("\n", " ")[:80]
            lines.append(f"| {r['id']} | {r['tag']} | {r['mode']} | {r['question']} | {got} |")
    if len(lines) == 4:
        lines.append("| none | | | | |")
    modes = Counter(r["mode"] for r in results if r["mode"])
    lines += ["", "## Cost by mode", ""] + [f"- {m}: {c}" for m, c in modes.most_common()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def dry_agent_and_judge(rows):
    """Fake agent: echoes the reference and calls the first expected tool. Fake judge: exact match."""
    by_q = {r["question"]: r for r in rows}

    def agent(q):
        return by_q[q]["reference"], [by_q[q]["expected_tools"].split("|")[0]]
    return agent, (lambda q, ref, ans: ref == ans)


def run_all(dry_run=False, write=True) -> tuple:
    rows = load_golden()
    if dry_run:
        agent, judge_fn = dry_agent_and_judge(rows)
        results = run_suite(agent, rows, judge_fn)
    else:
        results = run_suite(book_agent, rows)
    if write:
        (HERE / ("results.dryrun.json" if dry_run else "results.json")).write_text(json.dumps(results, indent=2))
        write_failures(results)
    return results, summarize(results)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--save-baseline", action="store_true")
    args = ap.parse_args()
    results, s = run_all(args.dry_run)
    if args.dry_run:
        print("DRY RUN: fake agent and judge, numbers are plumbing only.\n")
    print(f"accuracy {s['accuracy']:.1%}   tool accuracy {s['tool_accuracy']:.1%}   avg latency {s['avg_latency_s']:.2f}s")
    print(f"by tag: { {k: f'{v:.0%}' for k, v in s['accuracy_by_tag'].items()} }")
    print(f"failure modes: {s['failure_modes'] or 'none'}")
    if args.save_baseline and not args.dry_run:
        (HERE / "baseline.json").write_text(json.dumps({"accuracy": s["accuracy"]}))
        print("saved baseline.json")
