"""m3 memory processors and dynamic config."""
import unittest

from agentkit import llm
from agentkit.dynamic import config_for, pick_tools
from agentkit.memory import build_context, recall, token_limiter, tool_call_filter


def history():
    h = [{"role": "user", "content": "My dog is called Biscuit."},
         {"role": "assistant", "content": "Noted, Biscuit."}]
    for i in range(10):
        h += [{"role": "user", "content": f"filler question {i}"}, {"role": "assistant", "content": f"filler {i}"}]
    return h


class MemoryTests(unittest.TestCase):
    def test_recall_finds_an_old_fact(self):
        hits = recall("what is my dog called", history()[:-6], k=1)
        self.assertTrue(any("Biscuit" in m["content"] for m in hits))

    def test_build_context_starts_on_a_user_turn_and_ends_with_the_query(self):
        ctx = build_context(history(), "what is my dog called?", last_n=4)
        self.assertEqual(ctx[0]["role"], "user")
        self.assertEqual(ctx[-1]["content"], "what is my dog called?")
        self.assertTrue(any("Biscuit" in m["content"] for m in ctx if isinstance(m["content"], str)))

    def test_limiter_and_filter(self):
        msgs = [{"role": "user", "content": "x" * 400}, {"role": "user", "content": "short"}]
        self.assertEqual(len(token_limiter(msgs, 50)), 1)
        tool_turn = {"role": "assistant", "content": [{"type": "tool_use", "id": "1", "name": "t", "input": {}}]}
        self.assertEqual(tool_call_filter([tool_turn]), [])

    def test_query_over_limit_is_an_error(self):
        with self.assertRaises(ValueError):
            build_context([], "x" * 100, limit=5)


class DynamicTests(unittest.TestCase):
    def test_tiers_differ(self):
        free, ent = config_for("free"), config_for("enterprise")
        self.assertEqual(free.model, llm.SMALL_MODEL)
        self.assertIn("escalate", ent.allowed_tools)
        self.assertNotIn("lookup_order", free.allowed_tools)

    def test_unknown_tier_gets_least_access(self):
        self.assertEqual(config_for("platinum-ultra").tier, "free")

    def test_pick_tools(self):
        tools = [{"name": n} for n in ("lookup_order", "search_policy", "escalate")]
        self.assertEqual([t["name"] for t in pick_tools(config_for("free"), tools)], ["search_policy"])


if __name__ == "__main__":
    unittest.main()
