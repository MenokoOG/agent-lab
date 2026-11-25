"""Offline checks. Each test skips when its framework isn't installed in the active venv,
so you can run this file inside any one framework's venv.
"""
import importlib.util
import json
import unittest


def has(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:  # "google.adk" raises when "google" itself is missing
        return False


@unittest.skipUnless(has("pydantic_ai"), "pydantic-ai not installed")
class PydanticAITests(unittest.TestCase):
    def test_full_run_with_a_scripted_model(self):
        from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
        from pydantic_ai.models.function import FunctionModel
        import pydantic_ai_demo

        def script(messages, info):
            if len(messages) == 1:  # first turn: call the tool
                return ModelResponse(parts=[ToolCallPart("count_by", {"field": "genre"})])
            counts = json.loads(messages[-1].parts[0].content)  # the tool result we just got back
            top = max(counts, key=counts.get)
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"genre": top, "count": counts[top]})])

        result = pydantic_ai_demo.build(FunctionModel(script)).run_sync("x")
        self.assertEqual((result.output.genre, result.output.count), ("sci-fi", 8))


@unittest.skipUnless(has("agents") and has("litellm"), "openai-agents[litellm] not installed")
class OpenAIAgentsTests(unittest.TestCase):
    def test_builds_with_one_tool(self):
        import openai_agents_demo
        agent = openai_agents_demo.build()
        self.assertEqual([t.name for t in agent.tools], ["count_by"])


@unittest.skipUnless(has("crewai"), "crewai not installed")
class CrewAITests(unittest.TestCase):
    def test_builds_a_one_agent_crew(self):
        import crewai_demo
        crew = crewai_demo.build()
        self.assertEqual(len(crew.agents), 1)
        self.assertEqual(crewai_demo.count_by_tool.run(field="genre"), crewai_demo.count_by("genre"))


@unittest.skipUnless(has("google.adk") and has("litellm"), "google-adk and litellm not installed")
class ADKTests(unittest.TestCase):
    def test_builds_with_one_tool(self):
        import adk_demo
        agent = adk_demo.build()
        self.assertEqual(len(agent.tools), 1)


@unittest.skipUnless(has("claude_agent_sdk"), "claude-agent-sdk not installed")
class ClaudeAgentSDKTests(unittest.TestCase):
    def test_options_expose_only_the_book_tool(self):
        import asyncio
        import claude_agent_sdk_demo as demo
        opts = demo.options()
        self.assertEqual(opts.allowed_tools, ["mcp__books__count_by"])
        self.assertEqual(opts.tools, [])
        out = asyncio.run(demo.count_by_tool.handler({"field": "genre"}))
        self.assertEqual(json.loads(out["content"][0]["text"])["sci-fi"], 8)


if __name__ == "__main__":
    unittest.main()
