"""m1 prompts and m2 loop."""
import unittest

from agentkit import llm, prompts
from agentkit.loop import StepBudgetExhausted, run_agent
from tests.helpers import FakeModelTest

ECHO_TOOL = [{"name": "echo", "description": "Echo text. Call to test.",
              "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}}}]


class PromptTests(unittest.TestCase):
    def test_structured_wraps_every_part_in_tags(self):
        p = prompts.structured("Classify.", ["One word."], [("a", "b")], "ticket text")
        for tag in ("<task>", "<constraints>", "<examples>", "<input>ticket text</input>"):
            self.assertIn(tag, p)

    def test_few_shot_uses_every_example(self):
        shots = [("one", "1"), ("two", "2"), ("three", "3"), ("four", "4")]
        p = prompts.few_shot("T", "R", shots, "x")
        self.assertEqual(p.count("Input:"), 5)  # four examples plus the real item

    def test_few_shot_without_examples_is_an_error(self):
        with self.assertRaises(ValueError):
            prompts.few_shot("T", "R", [], "x")

    def test_pick_label_is_strict(self):
        self.assertEqual(prompts.pick_label(" Billing. ", ["billing"], "other"), "billing")
        self.assertEqual(prompts.pick_label("I think billing", ["billing"], "other"), "other")


class LoopTests(FakeModelTest):
    def test_tool_then_answer(self):
        fake = self.use(llm.scripted(llm.fake_tool_use("echo", {"text": "hi"}), llm.fake_text("done")))
        r = run_agent("go", ECHO_TOOL, {"echo": lambda text: text})
        self.assertEqual((r.answer, r.steps, r.tool_calls), ("done", 2, ["echo"]))
        self.assertEqual(fake.bodies[1]["messages"][-1]["content"][0]["content"], "hi")

    def test_tool_errors_reach_the_model(self):
        fake = self.use(llm.scripted(llm.fake_tool_use("echo", {"text": "x"}), llm.fake_text("ok")))

        def boom(text):
            raise ValueError("bad input")
        run_agent("go", ECHO_TOOL, {"echo": boom})
        result = fake.bodies[1]["messages"][-1]["content"][0]
        self.assertTrue(result["is_error"])
        self.assertIn("bad input", result["content"])

    def test_unknown_tool_is_surfaced_not_crashed(self):
        fake = self.use(llm.scripted(llm.fake_tool_use("nope", {}), llm.fake_text("ok")))
        run_agent("go", ECHO_TOOL, {})
        self.assertIn("unknown tool", fake.bodies[1]["messages"][-1]["content"][0]["content"])

    def test_step_budget(self):
        self.use(lambda body: llm.fake_tool_use("echo", {"text": "again"}))
        with self.assertRaises(StepBudgetExhausted):
            run_agent("go", ECHO_TOOL, {"echo": lambda text: text}, max_steps=3)


if __name__ == "__main__":
    unittest.main()
