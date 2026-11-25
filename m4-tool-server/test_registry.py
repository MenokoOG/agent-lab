import json
import unittest

import registry


class RegistryTests(unittest.TestCase):
    def test_every_description_says_when_to_call(self):
        for t in registry.list_tools():
            self.assertIn("Call", t["description"], t["name"])

    def test_list_tools_shape_matches_what_the_model_expects(self):
        for t in registry.list_tools():
            self.assertEqual(set(t), {"name", "description", "input_schema"})

    def test_call_tool(self):
        counts = json.loads(registry.call_tool("count_by", {"field": "genre"}))
        self.assertEqual(counts["sci-fi"], 8)

    def test_handlers_match_registry(self):
        self.assertEqual(set(registry.handlers()), set(registry.REGISTRY))

    def test_unknown_tool_raises(self):
        with self.assertRaises(KeyError):
            registry.call_tool("nope", {})


class McpTests(unittest.TestCase):
    def test_server_exposes_the_same_tools(self):
        try:
            import asyncio
            import server
        except ImportError:
            self.skipTest("mcp is not installed (pip install mcp)")
        listed = asyncio.run(server.mcp.list_tools())
        self.assertEqual({t.name for t in listed}, set(registry.REGISTRY))


if __name__ == "__main__":
    unittest.main()
