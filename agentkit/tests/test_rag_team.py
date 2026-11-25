"""m6 retrieval and m7 routing."""
import unittest

from agentkit import llm
from agentkit.rag import Index, chunk, rerank
from agentkit.team import Specialist, agent_as_tool, route, supervisor
from examples.desk_data import POLICIES
from tests.helpers import FakeModelTest


class RagTests(FakeModelTest):
    def test_chunk_overlap(self):
        parts = chunk("a" * 500, size=200, overlap=40)
        self.assertEqual(len(parts), 4)
        with self.assertRaises(ValueError):
            chunk("abc", size=10, overlap=10)

    def test_top_k_finds_the_right_document(self):
        idx = Index(POLICIES, size=160, overlap=30)
        self.assertEqual(idx.top_k("express shipping days", k=1)[0][0], "shipping.txt")

    def test_unknown_words_return_nothing(self):
        self.assertEqual(Index(POLICIES).top_k("zebra quantum"), [])

    def test_rerank_falls_back_on_a_bad_reply(self):
        self.use(lambda body: llm.fake_text("no idea"))
        hits = [("a", "one"), ("b", "two")]
        self.assertEqual(rerank("q", hits), hits)

    def test_rerank_follows_the_model(self):
        self.use(lambda body: llm.fake_text("1, 0"))
        self.assertEqual(rerank("q", [("a", "one"), ("b", "two")])[0][0], "b")


def specialists():
    return [Specialist("orders", "Order questions.", "orders"), Specialist("policy", "Policy questions.", "policy")]


class TeamTests(FakeModelTest):
    def test_route_parses_a_name(self):
        self.use(lambda body: llm.fake_text("Orders"))
        self.assertEqual(route("where is 1001", specialists()), "orders")

    def test_route_falls_back_to_default(self):
        self.use(lambda body: llm.fake_text("I would pick the billing team"))
        self.assertEqual(route("x", specialists(), default="policy"), "policy")

    def test_agent_as_tool_and_supervisor(self):
        tool, _ = agent_as_tool(specialists()[0])
        self.assertEqual(tool["name"], "ask_orders")
        self.use(llm.scripted(llm.fake_tool_use("ask_orders", {"brief": "1001?"}),
                              llm.fake_text("shipped"),       # the orders specialist answers
                              llm.fake_text("It shipped.")))  # the supervisor wraps up
        r = supervisor("where is 1001", specialists())
        self.assertEqual((r.answer, r.tool_calls), ("It shipped.", ["ask_orders"]))


if __name__ == "__main__":
    unittest.main()
