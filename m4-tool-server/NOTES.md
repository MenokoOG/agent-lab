# m4 tool-server notes

- My loop (`use_registry.py`) and an outside client both use the same four tools. The outside client is the Strands MCP client in F2: `python f2-strands/mcp_agent.py --list` printed `['list_genres', 'books_by_genre', 'recs_by_person', 'count_by']` on 2026-11-25.
- Every description says when to call it. `test_registry.py` checks for "Call".
- Client quirk: `mcp` 2.x renamed `FastMCP` to `MCPServer` and `Tool.inputSchema` to `input_schema`. `server.py` already handles the first. agentkit's `McpToolset` handles the second. Clients that pin 1.x and servers on 2.x will drift like this.
- Not done yet: point a desktop MCP client at `server.py` and call one tool by hand.
