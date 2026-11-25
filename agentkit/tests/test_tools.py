"""m2/m4 registry, the MCP server adapter, and the MCP client toolset."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

from agentkit.tools import McpToolset, Registry, serve_mcp, string_schema
from examples import desk_data

HAS_MCP = importlib.util.find_spec("mcp") is not None
SERVER = Path(__file__).resolve().parents[1] / "examples" / "desk_server.py"


class RegistryTests(unittest.TestCase):
    def test_description_must_say_when_to_call(self):
        r = Registry("t")
        with self.assertRaises(ValueError):
            r.tool("Adds numbers.")(lambda: 1)

    def test_list_and_call(self):
        r = Registry("t")

        @r.tool("Add two numbers. Call for sums.", string_schema(a="first", b="second"))
        def add(a, b):
            return int(a) + int(b)
        self.assertEqual(r.list_tools()[0]["name"], "add")
        self.assertEqual(r.call("add", {"a": "2", "b": "3"}), 5)
        with self.assertRaises(KeyError):
            r.call("missing", {})

    def test_desk_tools_shape(self):
        for t in desk_data.registry.list_tools():
            self.assertEqual(set(t), {"name", "description", "input_schema"})
        order = json.loads(desk_data.registry.call("lookup_order", {"order_id": "1001"}))
        self.assertEqual(order["status"], "shipped")


@unittest.skipUnless(HAS_MCP, "mcp is not installed")
class McpTests(unittest.TestCase):
    def test_server_exposes_the_registry(self):
        import asyncio
        listed = asyncio.run(serve_mcp(desk_data.registry).list_tools())
        self.assertEqual({t.name for t in listed}, {t["name"] for t in desk_data.registry.list_tools()})

    def test_client_calls_tools_over_stdio(self):
        toolset = McpToolset(sys.executable, [str(SERVER)])
        names = {t["name"] for t in toolset.list_tools()}
        self.assertEqual(names, {"lookup_order", "search_policy", "escalate"})
        self.assertIn("processing", toolset.handlers(["lookup_order"])["lookup_order"](order_id="1002"))

    def test_remote_tool_errors_are_raised(self):
        toolset = McpToolset(sys.executable, [str(SERVER)])
        with self.assertRaises(RuntimeError):
            toolset.call("lookup_order", {"order_id": "9999"})


if __name__ == "__main__":
    unittest.main()
