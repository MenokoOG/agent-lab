"""Offline tests: llm.FAKE stands in for the triage model, a scripted chat model for the agent graph."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402
import agent_graph  # noqa: E402
import triage_graph  # noqa: E402


class ScriptedChat(FakeMessagesListChatModel):
    """Returns the scripted messages in order. bind_tools is a no-op so the graph can use it."""

    def bind_tools(self, tools, **kwargs):
        return self


def fake_triage_model(urgent: bool):
    lock, seen = threading.Lock(), []

    def fake(body):
        prompt = body["messages"][-1]["content"]
        with lock:
            seen.append(prompt)
        if prompt.startswith("Classify"):
            return llm.fake_text("billing")
        if "handled today" in prompt:
            return llm.fake_text("yes" if urgent else "no")
        if prompt.startswith("Draft"):
            return llm.fake_text("Sorry about the double charge.")
        return llm.fake_text("yes")
    fake.seen = seen
    return fake


class TriageGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "runs.sqlite"
        self.savers = []

    def saver(self):
        s = triage_graph.open_saver(self.db)
        self.savers.append(s)
        return s

    def tearDown(self):
        llm.FAKE = None
        for s in self.savers:
            s.conn.close()
        self.tmp.cleanup()

    def run_until_pause(self, urgent=True, thread="t1"):
        llm.FAKE = fake_triage_model(urgent)
        graph = triage_graph.build(self.saver())
        cfg = {"configurable": {"thread_id": thread}}
        return graph.invoke({"email": "Charged twice, fix it today."}, cfg), cfg

    def test_pauses_at_approval_with_flags_merged(self):
        result, _ = self.run_until_pause()
        self.assertIn("__interrupt__", result)
        self.assertEqual(result["flags"], ["urgent", "angry", "refund"])
        self.assertEqual(result["priority"], "high")

    def test_resume_from_a_fresh_graph_like_a_restarted_process(self):
        _, cfg = self.run_until_pause()
        calls_before = len(llm.FAKE.seen)
        fresh = triage_graph.build(self.saver())  # new saver, new graph, same file
        done = fresh.invoke(Command(resume="yes"), cfg)
        self.assertEqual(done["reply"], "Sorry about the double charge.")
        self.assertEqual(len(llm.FAKE.seen) - calls_before, 1)  # only draft_reply called the model again

    def test_not_urgent_skips_priority(self):
        result, _ = self.run_until_pause(urgent=False)
        self.assertNotIn("priority", result)

    def test_declined_approval_drafts_nothing(self):
        _, cfg = self.run_until_pause()
        graph = triage_graph.build(self.saver())
        self.assertEqual(graph.invoke(Command(resume="no"), cfg)["reply"], "")

    def test_each_node_makes_at_most_one_llm_call(self):
        llm.FAKE = fake_triage_model(True)
        state = {"email": "x", "category": "billing", "flags": [], "approved": "yes"}
        for node in (triage_graph.classify, triage_graph.check_urgent, triage_graph.check_angry,
                     triage_graph.check_refund, triage_graph.draft_reply, triage_graph.merge_flags):
            before = len(llm.FAKE.seen)
            node(state)
            self.assertLessEqual(len(llm.FAKE.seen) - before, 1, node.__name__)


class AgentGraphTests(unittest.TestCase):
    def test_tool_roundtrip(self):
        model = ScriptedChat(responses=[
            AIMessage("", tool_calls=[{"name": "count_by", "args": {"field": "genre"}, "id": "c1"}]),
            AIMessage("sci-fi has the most, with 8."),
        ])
        r = agent_graph.ask("Which genre has the most books?", model=model)
        self.assertEqual(r["answer"], "sci-fi has the most, with 8.")
        self.assertEqual(r["tool_calls"], ["count_by"])
        self.assertEqual(r["messages"], 4)  # human, ai(tool call), tool result, ai(answer)

    def test_tool_error_goes_back_to_the_model(self):
        model = ScriptedChat(responses=[
            AIMessage("", tool_calls=[{"name": "count_by", "args": {"field": "colour"}, "id": "c1"}]),
            AIMessage("That field does not exist."),
        ])
        graph = agent_graph.build(model)
        out = graph.invoke({"messages": [("user", "count by colour")]})
        tool_msg = out["messages"][2]
        self.assertEqual(tool_msg.status, "error")
        self.assertIn("field must be one of", tool_msg.content)

    def test_step_budget(self):
        loop_forever = [AIMessage("", tool_calls=[{"name": "list_genres", "args": {}, "id": f"c{i}"}])
                        for i in range(50)]
        with self.assertRaises(GraphRecursionError):
            agent_graph.ask("x", model=ScriptedChat(responses=loop_forever), max_steps=3)


if __name__ == "__main__":
    unittest.main()
