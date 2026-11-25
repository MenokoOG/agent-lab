"""Run the three rungs over questions.json and print one table.

    python ladder.py            # needs ANTHROPIC_API_KEY
    python ladder.py --dry-run  # fake model, plumbing only
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402
import rung1_full  # noqa: E402
import rung2_tools  # noqa: E402
import rung3_rag  # noqa: E402

QUESTIONS = json.loads((Path(__file__).parent / "questions.json").read_text())
RUNGS = [("1 full context", rung1_full.answer), ("2 tools", rung2_tools.answer), ("3 rag", rung3_rag.answer)]


def correct(answer, must):
    return all(re.search(m, answer, re.I) for m in must)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        llm.FAKE = lambda body: llm.fake_text("dry run", tokens=len(str(body)) // 4)
        print("DRY RUN: fake model, numbers are plumbing only.\n")
    print(f"{'rung':<16}{'correct':>9}{'count/lookup':>14}{'avg in tok':>12}{'avg latency':>13}")
    print("-" * 64)
    for name, fn in RUNGS:
        ok, ok_hard, hard, toks, secs, wrong = 0, 0, 0, [], [], []
        for item in QUESTIONS:
            start = time.perf_counter()
            text, n_tok = fn(item["q"])
            secs.append(time.perf_counter() - start)
            toks.append(n_tok)
            good = correct(text, item["must"])
            ok += good
            if item["kind"] == "count":
                hard += 1
                ok_hard += good
            if not good:
                wrong.append(item["q"])
        n = len(QUESTIONS)
        print(f"{name:<16}{f'{ok}/{n}':>9}{f'{ok_hard}/{hard}':>14}{sum(toks) / n:>12.0f}{sum(secs) / n:>12.2f}s")
        for q in wrong:
            print(f"    missed: {q}")


if __name__ == "__main__":
    main()
