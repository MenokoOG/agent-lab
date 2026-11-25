import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm
from compact import compact, est_tokens
from experiment import PLANTED, compaction, make_turns, naive, structured
from repair import error_signature, prompt_hints, run_py, solve_with_repair
from state import State, compile_state, update_from_text


def fake_summary(old):
    return "SUMMARY"


class CompactTests(unittest.TestCase):
    def msgs(self, n):
        return [{"role": "user" if i % 2 == 0 else "assistant", "content": "word " * 200} for i in range(n)]

    def test_below_threshold_is_untouched(self):
        m = self.msgs(4)
        self.assertEqual(compact(m, threshold=10_000, summarize=fake_summary), m)

    def test_above_threshold_shrinks_and_keeps_the_last_turns(self):
        m = self.msgs(20)
        out = compact(m, threshold=500, keep_last=4, summarize=fake_summary)
        self.assertEqual(len(out), 5)
        self.assertEqual(out[-4:], m[-4:])
        self.assertLess(est_tokens(out), est_tokens(m))

    def test_a_must_keep_decision_survives_three_compactions(self):
        decision = "deploys happen on Tuesdays only"
        messages = self.msgs(20)
        for _ in range(3):
            messages = compact(messages, threshold=500, keep_last=4, must_keep=[decision], summarize=fake_summary)
            messages += self.msgs(10)
        messages = compact(messages, threshold=500, keep_last=4, must_keep=[decision], summarize=fake_summary)
        self.assertIn(decision, messages[0]["content"])


class StateTests(unittest.TestCase):
    def test_parse_and_compile(self):
        s = State(goal="g")
        update_from_text(s, "noise\nFACT: port is 8123\nDECISION: use Postgres\nQUESTION: who owns it?")
        out = compile_state(s)
        for needle in ("8123", "Postgres", "who owns it?", "Goal: g"):
            self.assertIn(needle, out)
        self.assertNotIn("noise", out)


class RepairTests(unittest.TestCase):
    def test_run_py(self):
        self.assertEqual(run_py("print('hi')")[:2], (0, "hi\n"))
        rc, _, err = run_py("raise ValueError('boom')")
        self.assertNotEqual(rc, 0)
        self.assertEqual(error_signature(err), "ValueError: boom")

    def test_repair_loop_fixes_the_code_and_hints_on_a_repeat(self):
        replies = iter(["print(undefined)", "print(also_undefined)", "print('fixed')"])
        out, hints = solve_with_repair("say fixed", ask=lambda p: next(replies))
        self.assertEqual(out.strip(), "fixed")
        self.assertEqual(hints, [])  # two different errors, no repeat

    def test_repeated_error_produces_a_prompt_hint(self):
        replies = iter(["import nope_a", "import nope_a", "print('ok')"])
        out, hints = solve_with_repair("x", ask=lambda p: next(replies))
        self.assertEqual(len(hints), 1)
        self.assertIn("ModuleNotFoundError", hints[0])

    def test_retry_cap(self):
        with self.assertRaises(RuntimeError):
            solve_with_repair("x", max_tries=2, ask=lambda p: "raise SystemError('no')")

    def test_hints_threshold(self):
        self.assertEqual(prompt_hints(Counter({"E": 1})), [])
        self.assertEqual(len(prompt_hints(Counter({"E": 2}))), 1)


class ExperimentTests(unittest.TestCase):
    def tearDown(self):
        llm.FAKE = None

    def test_planted_facts_are_in_the_turns(self):
        turns = make_turns(60, 20)
        self.assertEqual(len(turns), 60)
        for t, line, _, _ in PLANTED:
            self.assertIn(line, turns[t - 1])

    def test_structured_context_is_much_smaller_than_naive(self):
        turns = make_turns(60, 120)
        naive_msgs, _ = naive(turns)
        text, _ = structured(turns)
        self.assertLess(len(text), 0.1 * sum(len(m["content"]) for m in naive_msgs))
        self.assertIn("8123", text)

    def test_compaction_strategy_keeps_decisions_with_a_fake_summarizer(self):
        llm.FAKE = lambda body: llm.fake_text("SUMMARY")
        turns = make_turns(60, 120)
        messages, n = compaction(turns, threshold=1500)
        self.assertGreater(n, 0)
        joined = " ".join(m["content"] for m in messages if isinstance(m["content"], str))
        self.assertIn("Postgres", joined)
        self.assertIn("Tuesdays", joined)


if __name__ == "__main__":
    unittest.main()
