"""A scripted long run. Compare naive append, compaction and structured context.

    python experiment.py --dry-run               # fake model, plumbing only
    python experiment.py                         # real run, needs ANTHROPIC_API_KEY
    python experiment.py --filler 400 --turns 120   # make the run longer to see degradation

Caveat: the structured strategy parses FACT:/DECISION: markers with code, so it gets those lines for free.
It shows the upper bound of what clean structure buys you, not what an agent would extract on its own.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402
from compact import compact, est_tokens, llm_summarize  # noqa: E402
from state import State, compile_state, update_from_text  # noqa: E402

# (turn number, line, question, regex the answer must match)
PLANTED = [
    (3, "FACT: the staging server port is 8123", "What port does the staging server use?", r"8123"),
    (9, "DECISION: we chose Postgres over MySQL for the orders table", "Which database did we choose for the orders table?", r"postgres"),
    (15, "FACT: the release codename is Bluefin", "What is the release codename?", r"bluefin"),
    (24, "FACT: the on-call engineer is Marta", "Who is the on-call engineer?", r"marta"),
    (33, "DECISION: deploys happen on Tuesdays only", "On which day do deploys happen?", r"tuesday"),
]


def make_turns(n_turns: int, filler_words: int) -> list:
    planted = {t: line for t, line, _, _ in PLANTED}
    filler = " ".join(["routine", "status", "update", "nothing", "new", "to", "report"] * (filler_words // 7 + 1))
    filler = " ".join(filler.split()[:filler_words])
    return [f"Turn {i}: {filler}" + (f"\n{planted[i]}" if i in planted else "") for i in range(1, n_turns + 1)]


def ask_questions(context_text_or_messages, calls: dict) -> tuple:
    """Ask each planted question against the final context. Returns (correct, avg input tokens)."""
    correct, tokens = 0, []
    for _, _, q, pattern in PLANTED:
        if isinstance(context_text_or_messages, str):
            messages = [{"role": "user", "content": f"{context_text_or_messages}\n\nQuestion: {q}\nAnswer briefly."}]
        else:
            messages = context_text_or_messages + [{"role": "user", "content": f"Question: {q}\nAnswer briefly."}]
        resp = llm.chat(messages)
        calls["n"] += 1
        tokens.append(resp["usage"]["input_tokens"])
        correct += bool(re.search(pattern, llm.text_of(resp), re.I))
    return correct, sum(tokens) / len(tokens)


def naive(turns):
    messages = []
    for t in turns:
        messages += [{"role": "user", "content": t}, {"role": "assistant", "content": "Noted."}]
    return messages, 0


def compaction(turns, threshold=1500):
    messages, summaries, must = [], [0], []  # must accumulates: old turns vanish after a compaction

    def counting_summarize(old):
        summaries[0] += 1
        return llm_summarize(old)

    for t in turns:
        messages += [{"role": "user", "content": t}, {"role": "assistant", "content": "Noted."}]
        must += [line[len("DECISION:"):].strip() for line in t.splitlines() if line.startswith("DECISION:")]
        messages = compact(messages, threshold, keep_last=4, must_keep=must, summarize=counting_summarize)
    return messages, summaries[0]


def structured(turns):
    state = State(goal="Keep track of the project facts and decisions.")
    for t in turns:
        update_from_text(state, t)
    return compile_state(state), 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--turns", type=int, default=60)
    ap.add_argument("--filler", type=int, default=120, help="words of filler per turn")
    args = ap.parse_args()
    if args.dry_run:
        llm.FAKE = lambda body: llm.fake_text("dry run", tokens=est_tokens(body["messages"]))
        print("DRY RUN: fake model, numbers are plumbing only.\n")
    turns = make_turns(args.turns, args.filler)
    print(f"{args.turns} turns, ~{args.filler} filler words each\n")
    print(f"{'strategy':<14}{'correct':>9}{'avg in tok':>12}{'summary calls':>15}")
    print("-" * 50)
    for name, build in [("naive append", naive), ("compaction", compaction), ("structured", structured)]:
        context, summaries = build(turns)
        calls = {"n": 0}
        correct, avg_tokens = ask_questions(context, calls)
        print(f"{name:<14}{f'{correct}/{len(PLANTED)}':>9}{avg_tokens:>12.0f}{summaries:>15}")


if __name__ == "__main__":
    main()
