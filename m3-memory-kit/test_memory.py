import unittest

from demo import make_history
from dynamic import config_for, pick_tools
from memory import build_context, est_tokens, msg_text, recall, tool_call_filter, token_limiter


class MemoryTests(unittest.TestCase):
    def test_build_context_never_exceeds_the_limit(self):
        history = make_history(60)
        for limit in (80, 150, 400, 2000):
            ctx = build_context(history, "What is my dog allergic to?", limit=limit)
            total = sum(est_tokens(msg_text(m)) for m in ctx)
            self.assertLessEqual(total, limit, f"limit {limit}")

    def test_recall_pulls_an_old_message_the_window_dropped(self):
        history = make_history(30)
        ctx = build_context(history, "What is my dog allergic to?", last_n=6, top_k=1, limit=2000)
        texts = [msg_text(m) for m in ctx]
        self.assertTrue(any("allergic to chicken" in t for t in texts))
        self.assertNotIn(history[2], history[-6:])

    def test_recall_includes_neighbours(self):
        history = make_history(30)
        got = recall("dog allergic chicken", history, k=1, rng=1)
        self.assertEqual(len(got), 3)

    def test_recall_empty_history(self):
        self.assertEqual(recall("anything", []), [])

    def test_token_limiter_drops_oldest_first(self):
        msgs = [{"role": "user", "content": "a" * 400}, {"role": "user", "content": "b" * 40}]
        kept = token_limiter(msgs, 50)
        self.assertEqual([m["content"][0] for m in kept], ["b"])

    def test_tool_call_filter(self):
        msgs = [
            {"role": "assistant", "content": [{"type": "text", "text": "checking"},
                                              {"type": "tool_use", "id": "1", "name": "x", "input": {}}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "1", "content": "big"}]},
            {"role": "user", "content": "plain"},
        ]
        out = tool_call_filter(msgs)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["content"], [{"type": "text", "text": "checking"}])

    def test_query_alone_over_limit_raises(self):
        with self.assertRaises(ValueError):
            build_context([], "x" * 400, limit=10)


class DynamicTests(unittest.TestCase):
    def test_tier_changes_model_prompt_and_tools_without_a_new_class(self):
        free, ent = config_for("free", "Spanish"), config_for("enterprise", "Spanish")
        self.assertNotEqual(free.model, ent.model)
        self.assertNotEqual(free.system, ent.system)
        self.assertLess(len(free.tool_names), len(ent.tool_names))
        self.assertIn("Spanish", free.system)

    def test_pick_tools(self):
        all_tools = [{"name": n} for n in ("search_docs", "lookup_account", "escalate")]
        names = [t["name"] for t in pick_tools(config_for("pro", "English"), all_tools)]
        self.assertEqual(names, ["search_docs", "lookup_account"])


if __name__ == "__main__":
    unittest.main()