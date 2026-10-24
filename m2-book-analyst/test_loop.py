import json
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402
import tools  # noqa: E402
from compare import build_questions, score  # noqa: E402
from loop import run_agent  # noqa: E402


class LoopTests(unittest.TestCase):
    def tearDown(self):
        llm.FAKE = None

    def test_tool_roundtrip(self):
        llm.FAKE = llm.scripted(llm.fake_tool_use("count_by", {"field": "genre"}),
                                llm.fake_text("sci-fi has 8"))
        r = run_agent("count genres", tools.TOOLS, tools.HANDLERS)
        self.assertEqual((r.answer, r.steps, r.tool_calls), ("sci-fi has 8", 2, ["count_by"]))
        result_msg = llm.FAKE.bodies[1]["messages"][-1]["content"][0]
        self.assertFalse(result_msg["is_error"])
        self.assertIn("sci-fi", result_msg["content"])

    def test_tool_error_is_surfaced_to_the_model(self):
        llm.FAKE = llm.scripted(llm.fake_tool_use("count_by", {"field": "colour"}),
                                llm.fake_text("that field does not exist"))
        run_agent("x", tools.TOOLS, tools.HANDLERS)
        result_msg = llm.FAKE.bodies[1]["messages"][-1]["content"][0]
        self.assertTrue(result_msg["is_error"])
        self.assertIn("error", result_msg["content"])

    def test_step_budget(self):
        llm.FAKE = lambda body: llm.fake_tool_use("list_genres", {})
        with self.assertRaises(RuntimeError):
            run_agent("loop forever", tools.TOOLS, tools.HANDLERS, max_steps=3)

    def test_accepts_a_message_list(self):
        llm.FAKE = llm.scripted(llm.fake_text("ok"))
        r = run_agent([{"role": "user", "content": "hi"}], [], {})
        self.assertEqual(r.answer, "ok")


class DataTests(unittest.TestCase):
    def test_thirty_rows_two_filterable_fields(self):
        self.assertEqual(len(tools.ROWS), 30)

    def test_answers_are_unambiguous(self):
        for field in ("genre", "recommender"):
            top = Counter(r[field] for r in tools.ROWS).most_common(2)
            self.assertGreater(top[0][1], top[1][1], f"tie for most common {field}")

    def test_tools(self):
        self.assertEqual(json.loads(tools.count_by("genre"))["sci-fi"], 8)
        self.assertEqual(len(json.loads(tools.recs_by_person("priya"))), 7)

    def test_scoring(self):
        qs = build_questions(tools.ROWS)
        self.assertTrue(score("There are 8 sci-fi books.", qs[0]["must"]))
        self.assertFalse(score("There are 18 sci-fi books.", qs[0]["must"]))


if __name__ == "__main__":
    unittest.main()