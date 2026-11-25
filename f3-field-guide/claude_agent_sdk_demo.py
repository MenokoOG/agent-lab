"""Claude Agent SDK: the harness behind Claude Code, as a library. Files, shell, subagents and hooks built in.
Your own tools plug in as an in-process MCP server.

    pip install claude-agent-sdk
    python claude_agent_sdk_demo.py
"""
import asyncio

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, create_sdk_mcp_server, query, tool

from shared import INSTRUCTIONS, MODEL, QUESTION, count_by


@tool("count_by", "Count books grouped by genre, recommender or author.", {"field": str})
async def count_by_tool(args: dict) -> dict:
    return {"content": [{"type": "text", "text": count_by(args["field"])}]}


def options() -> ClaudeAgentOptions:
    books = create_sdk_mcp_server(name="books", version="1.0.0", tools=[count_by_tool])
    return ClaudeAgentOptions(
        model=MODEL,
        system_prompt=INSTRUCTIONS,
        mcp_servers={"books": books},
        allowed_tools=["mcp__books__count_by"],  # MCP tools are named mcp__<server>__<tool>
        tools=[],       # turn off the built-in file and shell tools: this agent only counts books
        max_turns=4,    # the step budget
    )


async def main() -> None:
    async for message in query(prompt=QUESTION, options=options()):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)


if __name__ == "__main__":
    asyncio.run(main())
