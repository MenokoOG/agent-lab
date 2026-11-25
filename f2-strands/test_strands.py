"""Offline tests with a scripted model. No API key, no AWS account."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import book_agent  # noqa: E402
import team  # noqa: E402
from fake_model import ScriptedModel  # noqa: E402


def tool_results(model: ScriptedModel) -> list:
    """Every toolResult block the agent sent back to the model, across all requests."""
    seen = {}
    for req in model.requests:
        for m in req["messages"]:
            for block in m["content"]:
                if "toolResult" in block:
                    seen[block["toolResult"]["toolUseId"]] = block["toolResult"]
    return list(seen.values())


class BookAgentTests(unittest.TestCase):
    def test_schema_comes_from_type_hints_and_docstring(self):
        spec = book_agent.count_by.tool_spec
        self.assertIn("Call for any how-many", spec["description"])
        self.assertEqual(spec["inputSchema"]["json"]["required"], ["field"])
        self.assertIn("genre", spec["inputSchema"]["json"]["properties"]["field"]["description"])

    def test_tool_roundtrip(self):
        model = ScriptedModel(("tool", "count_by", {"field": "genre"}), "sci-fi has the most, with 8.")
        agent = book_agent.build_agent(model)
        result = agent("Which genre has the most books?")
        self.assertEqual(str(result).strip(), "sci-fi has the most, with 8.")
        (res,) = tool_results(model)
        self.assertEqual(res["status"], "success")
        self.assertEqual(json.loads(res["content"][0]["text"])["sci-fi"], 8)
        self.assertEqual(model.requests[0]["system"], book_agent.SYSTEM)

    def test_tool_error_is_surfaced_to_the_model(self):
        model = ScriptedModel(("tool", "count_by", {"field": "colour"}), "That field does not exist.")
        book_agent.build_agent(model)("count by colour")
        (res,) = tool_results(model)
        self.assertEqual(res["status"], "error")
        self.assertIn("field must be one of", res["content"][0]["text"])

    def test_direct_tool_call_without_the_model(self):
        agent = book_agent.build_agent(ScriptedModel())
        out = agent.tool.recs_by_person(person="priya")
        self.assertEqual(len(json.loads(out["content"][0]["text"])), 7)


class TeamTests(unittest.TestCase):
    def test_router_reaches_a_leaf_tool_through_one_specialist(self):
        scripts = iter([
            ScriptedModel(("tool", "get_order", {"order_id": "1002"}), "Order 1002 is processing."),  # orders
            ScriptedModel(),                                                                         # catalog
            ScriptedModel(("tool", "ask_orders", {"brief": "Where is order 1002?"}), "It is processing."),  # router
        ])
        models = []

        def make_model():
            models.append(next(scripts))
            return models[-1]

        router, _, _ = team.build_team(make_model)
        self.assertEqual(str(router("Where is order 1002?")).strip(), "It is processing.")
        orders_model, catalog_model, router_model = models
        self.assertEqual(set(router_model.requests[0]["tools"]), {"ask_orders", "ask_catalog"})
        self.assertEqual(set(orders_model.requests[0]["tools"]), {"get_order", "list_orders"})
        self.assertEqual(catalog_model.requests, [])  # never called
        (leaf,) = tool_results(orders_model)
        self.assertEqual(json.loads(leaf["content"][0]["text"])["status"], "processing")


class McpTests(unittest.TestCase):
    def test_strands_lists_the_module_4_server_tools(self):
        try:
            import mcp_agent
        except ImportError:
            self.skipTest("mcp not installed")
        with mcp_agent.m4_client() as client:
            names = {t.tool_name for t in client.list_tools_sync()}
        self.assertEqual(names, {"list_genres", "books_by_genre", "recs_by_person", "count_by"})


class AgentCoreTests(unittest.TestCase):
    def test_entrypoint_answers_over_http(self):
        try:
            from starlette.testclient import TestClient
            import agentcore_app
        except ImportError:
            self.skipTest("bedrock-agentcore not installed")
        agentcore_app._agent = book_agent.build_agent(ScriptedModel("There are 5 genres."))
        client = TestClient(agentcore_app.app)
        r = client.post("/invocations", json={"prompt": "How many genres?"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("5 genres", r.json()["result"])
        self.assertIn("error", client.post("/invocations", json={}).json())


if __name__ == "__main__":
    unittest.main()
