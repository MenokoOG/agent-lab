"""Module 4's MCP server, used by a Strands agent. Same tools, a client you didn't write.

    python mcp_agent.py --list                       # starts the m4 server and lists its tools (no API key)
    python mcp_agent.py "Which genre has the most books?"
"""
import sys
from pathlib import Path

from mcp import StdioServerParameters, stdio_client
from strands import Agent
from strands.tools.mcp import MCPClient

SERVER = Path(__file__).resolve().parents[1] / "m4-tool-server" / "server.py"


def m4_client() -> MCPClient:
    # Launches your module 4 server as a child process and talks to it over stdio.
    return MCPClient(lambda: stdio_client(StdioServerParameters(
        command=sys.executable, args=[str(SERVER)], cwd=str(SERVER.parent))))


if __name__ == "__main__":
    client = m4_client()
    with client:  # the server runs only inside this block
        tools = client.list_tools_sync()
        if sys.argv[1:] == ["--list"]:
            print([t.tool_name for t in tools])
        else:
            from models import make_model
            agent = Agent(model=make_model(), tools=tools, callback_handler=None,
                          system_prompt="You analyze a book corpus. Use the tools.")
            print(agent(" ".join(sys.argv[1:]) or "Which genre has the most books?"))
