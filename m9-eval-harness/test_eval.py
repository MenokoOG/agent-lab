import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm
import gate
import suite
from judge import agreement, judge


class GoldenTests(unittest.TestCase):
    def test_thirty_unique_rows_with_tags_and_expected_tools(self):
        rows = suite.load_golden()
        self.assertEqual(len(rows), 30)
        self.assertEqual(len({r["id"] for r in rows}), 30)
        for r in rows:
            self.assertTrue(r["reference"] and r["tag"] and r["expected_tools"])

    def test_references_match_the_corpus(self):
        rows = {r["question"]: r["reference"] for r in suite.load_golden()}
        self.assertEqual(rows["How many books are in the sci-fi genre?"], "8 books.")
        self.assertEqual(rows["Which person recommended the most books?"], "Priya")


class SuiteTests(unittest.TestCase):
    def tearDown(self):
        llm.FAKE = None

    def test_dry_run_scores_everything_and_writes_nothing_when_told(self):
        results, s = suite.run_all(dry_run=True, write=False)
        self.assertEqual((s["n"], s["accuracy"], s["tool_accuracy"]), (30, 1.0, 1.0))

    def test_failure_modes(self):
        self.assertEqual(suite.failure_mode(True, True), "budget_or_error")
        self.assertEqual(suite.failure_mode(False, False), "wrong_tool")
        self.assertEqual(suite.failure_mode(False, True), "wrong_answer")

    def test_broken_agent_fails_and_is_tagged(self):
        rows = suite.load_golden()[:3]

        def wrong_tool_agent(q):
            return "no idea", ["list_genres"] if "count" not in q else []

        def exploding_agent(q):
            raise RuntimeError("step budget exhausted")

        r1 = suite.run_suite(wrong_tool_agent, rows, lambda q, ref, ans: False)
        self.assertTrue(all(r["mode"] in ("wrong_tool", "wrong_answer") for r in r1))
        r2 = suite.run_suite(exploding_agent, rows, lambda q, ref, ans: True)
        self.assertTrue(all(r["mode"] == "budget_or_error" and not r["passed"] for r in r2))

    def test_judge_parses_pass_and_fail(self):
        llm.FAKE = lambda body: llm.fake_text("PASS")
        self.assertTrue(judge("q", "r", "a"))
        llm.FAKE = lambda body: llm.fake_text("FAIL")
        self.assertFalse(judge("q", "r", "a"))
        llm.FAKE = lambda body: llm.fake_text("pass.")
        self.assertTrue(judge("q", "r", "a"))

    def test_failures_md(self):
        rows = suite.load_golden()[:2]
        results = suite.run_suite(lambda q: ("wrong", []), rows, lambda q, ref, ans: False)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "FAILURES.md"
            suite.write_failures(results, path)
            text = path.read_text()
        self.assertIn("| g01 |", text)
        self.assertIn("Cost by mode", text)


class GateTests(unittest.TestCase):
    def test_gate_logic(self):
        self.assertTrue(gate.passes(0.90, 0.90))
        self.assertTrue(gate.passes(0.895, 0.90))
        self.assertFalse(gate.passes(0.80, 0.90))

    def test_gate_fails_the_build_when_the_agent_is_broken(self):
        old = gate.BASELINE
        with tempfile.TemporaryDirectory() as d:
            gate.BASELINE = Path(d) / "baseline.json"
            self.assertEqual(gate.main(["--dry-run"]), 2)  # no baseline yet
            gate.BASELINE.write_text(json.dumps({"accuracy": 1.0}))
            self.assertEqual(gate.main(["--dry-run"]), 0)  # dry-run agent is perfect
            real_dry = suite.dry_agent_and_judge
            suite.dry_agent_and_judge = lambda rows: (lambda q: ("garbage", ["count_by"]), lambda q, ref, ans: ref == ans)
            try:
                self.assertEqual(gate.main(["--dry-run"]), 1)  # break it on purpose, the gate fails
            finally:
                suite.dry_agent_and_judge = real_dry
        gate.BASELINE = old


class AgreementTests(unittest.TestCase):
    def test_agreement(self):
        n, agree, bad = agreement({"a": True, "b": False, "c": True}, {"a": True, "b": True})
        self.assertEqual((n, agree, bad), (2, 1, ["b"]))

    def test_hand_grade_template_lists_ten_real_ids(self):
        ids = {r["id"] for r in suite.load_golden()}
        with open(Path(__file__).parent / "hand_grades.csv", newline="") as f:
            hand = [r["id"] for r in csv.DictReader(f)]
        self.assertEqual(len(hand), 10)
        self.assertTrue(set(hand) <= ids)


if __name__ == "__main__":
    unittest.main()
