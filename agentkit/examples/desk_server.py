"""The support desk tools as an MCP server over stdio.

    python examples/desk_server.py
Any MCP client can call these. support_desk.py launches this file itself unless you pass --local.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so the script runs without an install

from agentkit.tools import serve_mcp  # noqa: E402
from examples.desk_data import registry  # noqa: E402

server = serve_mcp(registry)

if __name__ == "__main__":
    server.run()
