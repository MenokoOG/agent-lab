"""m8 compaction, structured state and the repair loop."""
import unittest

from agentkit.context import State, compact, compile_state, repair_loop, run_py, update_from_text


def long_thread(n=20):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"message {i} " + "x" * 80}
            for i in range(n)]


class CompactTests(unittest.TestCase):
    def test_under_threshold_is_untouched(self):
        msgs = long_thread(2)
        self.assertIs(compact(msgs, threshold=10_000), msgs)

    def test_decision_survives_three_compactions(self):
        msgs = long_thread()
        for _ in range(3):
            msgs = compact(msgs, threshold=50, keep_last=4, must_keep=["refund 1001 approved"],
                           summarize=lambda old: "summary")
            msgs += long_thread(6)
        self.assertIn("refund 1001 approved", msgs[0]["content"])

    def test_result_starts_on_a_user_turn(self):
        # 9 messages: the last 4 start on an assistant turn, which compact must drop.
        out = compact(long_thread(9), threshold=50, keep_last=4, summarize=lambda old: "s")
        self.assertEqual(out[0]["role"], "user")
        self.assertEqual(out[1]["role"], "user")
        self.assertEqual(len(out), 4)


class StateTests(unittest.TestCase):
    def test_prefixed_lines_are_kept_once(self):
        s = State("help Ana")
        update_from_text(s, "DECISION: refund\nchatter\nFACT: order 1001\nDECISION: refund")
        self.assertEqual((s.decisions, s.facts), (["refund"], ["order 1001"]))
        self.assertIn("- refund", compile_state(s))


class RepairTests(unittest.TestCase):
    def test_feeds_the_error_back_and_succeeds(self):
        answers = iter(["print(1/0)", "print('fixed')"])
        out, errors = repair_loop("x", ask=lambda prompt: next(answers))
        self.assertEqual(out.strip(), "fixed")
        self.assertEqual(sum(errors.values()), 1)

    def test_gives_up_after_max_tries(self):
        with self.assertRaises(RuntimeError):
            repair_loop("x", ask=lambda prompt: "raise SystemExit(3)", max_tries=2)

    def test_run_py_reports_timeouts(self):
        rc, _, err = run_py("while True: pass", timeout=1)
        self.assertEqual(rc, 1)
        self.assertIn("Timeout", err)


if __name__ == "__main__":
    unittest.main()
