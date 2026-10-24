"""Attempt 1 (dump the whole corpus in the prompt) vs attempt 2 (tools + loop) on the same questions.

    export ANTHROPIC_API_KEY=...
    python compare.py            # real run
    python compare.py --dry-run  # fake model, checks the plumbing only
"""
import argparse
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402
import tools  # noqa: E402
from loop import run_agent  # noqa: E402

SYSTEM = "You analyze a book corpus. Use the tools for counts and lists. Answer briefly."


def build_questions(rows):
    """Questions with answers computed from the data, so the expected values can't drift."""
    by_genre = Counter(r["genre"] for r in rows)
    by_rec = Counter(r["recommender"] for r in rows)
    top_genre = by_genre.most_common(1)[0][0]
    top_rec = by_rec.most_common(1)[0][0]
    rec_titles = [r["title"] for r in rows if r["recommender"] == top_rec]
    return [
        {"q": f"How many books are in the {top_genre} genre?", "must": [rf"\b{by_genre[top_genre]}\b"]},
        {"q": "Which genre has the most books?", "must": [re.escape(top_genre)]},
        {"q": f"List every title {top_rec} recommended.", "must": [re.escape(t) for t in rec_titles]},
        {"q": "How many different people made recommendations?", "must": [rf"\b{len(by_rec)}\b"]},
        {"q": "Which person recommended the most books?", "must": [re.escape(top_rec)]},
    ]


def score(answer, must):
    return all(re.search(m, answer, re.I) for m in must)


def attempt1(q):
    """Whole corpus in the prompt, one call."""
    corpus = tools.BOOKS.read_text(encoding="utf-8")
    resp = llm.chat([{"role": "user", "content": f"Book corpus (CSV):\n{corpus}\n\nQuestion: {q}\nAnswer briefly."}])
    return llm.text_of(resp), 1, resp["usage"]["input_tokens"]


def attempt2(q):
    """Tools plus the loop."""
    try:
        r = run_agent(q, tools.TOOLS, tools.HANDLERS, system=SYSTEM)
        return r.answer, r.steps, r.input_tokens
    except RuntimeError as e:
        return f"[{e}]", 8, 0


def evaluate(name, fn, questions):
    correct, steps, tokens, secs = 0, [], [], []
    for item in questions:
        start = time.perf_counter()
        answer, n_steps, n_tokens = fn(item["q"])
        secs.append(time.perf_counter() - start)
        steps.append(n_steps)
        tokens.append(n_tokens)
        correct += score(answer, item["must"])
        print(f"  [{'ok' if score(answer, item['must']) else 'XX'}] {item['q']}")
    n = len(questions)
    return name, correct, n, sum(steps) / n, sum(tokens) / n, sum(secs) / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        llm.FAKE = lambda body: llm.fake_text("dry run", tokens=len(str(body)) // 4)
    questions = build_questions(tools.ROWS)
    rows = []
    for name, fn in [("1 dump corpus", attempt1), ("2 tools + loop", attempt2)]:
        print(name)
        rows.append(evaluate(name, fn, questions))
    if args.dry_run:
        print("\nDRY RUN: fake model, numbers are plumbing only.")
    print(f"\n{'attempt':<16}{'correct':>9}{'avg steps':>11}{'avg in tok':>12}{'avg latency':>13}")
    print("-" * 61)
    for name, c, n, st, tok, sec in rows:
        print(f"{name:<16}{f'{c}/{n}':>9}{st:>11.1f}{tok:>12.0f}{sec:>12.2f}s")


if __name__ == "__main__":
    main()