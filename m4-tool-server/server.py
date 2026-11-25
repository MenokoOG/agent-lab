"""Step 2: the same tools as an MCP server (pip install mcp). Run: python server.py

Step 3: point an MCP client (an editor or desktop assistant) at it. Example client config:
  {"mcpServers": {"books": {"command": "python", "args": ["/full/path/to/server.py"]}}}
"""
try:
    from mcp.server.fastmcp import FastMCP as Server       # mcp 1.x
except ImportError:
    from mcp.server.mcpserver import MCPServer as Server   # mcp 2.x renamed it

import registry

mcp = Server("books")

for name, t in registry.REGISTRY.items():
    mcp.add_tool(t["fn"], name=name, description=t["description"])

if __name__ == "__main__":
    mcp.run()  # stdio transport, which is what desktop clients expect
