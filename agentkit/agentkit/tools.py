"""m2/m4: a tool registry, the MCP server adapter, and an MCP client toolset.

The registry is what MCP standardizes: list tools, call a tool. serve_mcp() exposes a registry to any
MCP client. McpToolset goes the other way and turns a running MCP server into tools plus handlers
for run_agent, so the agent loop can't tell whether a tool is local or remote.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


def string_schema(**props: str) -> dict:
    """Object schema where every property is a required string."""
    return {"type": "object",
            "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props)}


@dataclass
class Registry:
    name: str
    _tools: Dict[str, dict] = field(default_factory=dict)

    def tool(self, description: str, schema: Optional[dict] = None) -> Callable:
        if "Call" not in description:
            raise ValueError("a tool description must say when to call it (include 'Call ...')")

        def wrap(fn: Callable) -> Callable:
            self._tools[fn.__name__] = {"fn": fn, "description": description,
                                        "schema": schema or {"type": "object", "properties": {}}}
            return fn
        return wrap

    def list_tools(self, names: Optional[List[str]] = None) -> List[dict]:
        return [{"name": n, "description": t["description"], "input_schema": t["schema"]}
                for n, t in self._tools.items() if names is None or n in names]

    def handlers(self, names: Optional[List[str]] = None) -> Dict[str, Callable]:
        return {n: t["fn"] for n, t in self._tools.items() if names is None or n in names}

    def call(self, name: str, args: dict) -> object:
        if name not in self._tools:
            raise KeyError(f"unknown tool {name}")
        return self._tools[name]["fn"](**args)


def serve_mcp(registry: Registry):
    """Build an MCP server with the registry's tools. Call .run() on the result for stdio."""
    try:
        from mcp.server.fastmcp import FastMCP as Server  # mcp 1.x
    except ImportError:
        from mcp.server.mcpserver import MCPServer as Server  # mcp 2.x renamed it
    server = Server(registry.name)
    for name, t in registry._tools.items():
        server.add_tool(t["fn"], name=name, description=t["description"])
    return server


def _schema_of(tool) -> dict:
    """mcp 1.x calls it inputSchema, 2.x calls it input_schema."""
    schema = getattr(tool, "input_schema", None) or getattr(tool, "inputSchema", None)
    return schema or {"type": "object", "properties": {}}


class McpToolset:
    """Tools from an MCP server launched over stdio.

    Each call opens a short session. That costs a process start per call, which is fine for a demo
    and keeps this class free of background threads. A long-running service would hold one session.
    """

    def __init__(self, command: str, args: List[str], cwd: Optional[str] = None):
        from mcp import StdioServerParameters
        self.params = StdioServerParameters(command=command, args=args, cwd=cwd)
        self._listed: Optional[List[dict]] = None  # a server's tool list is fixed for its lifetime

    async def _with_session(self, work):
        from mcp import ClientSession, stdio_client
        async with stdio_client(self.params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await work(session)

    def list_tools(self, names: Optional[List[str]] = None) -> List[dict]:
        if self._listed is None:
            async def work(s):
                return (await s.list_tools()).tools
            self._listed = [{"name": t.name, "description": t.description or "", "input_schema": _schema_of(t)}
                            for t in asyncio.run(self._with_session(work))]
        return [t for t in self._listed if names is None or t["name"] in names]

    def call(self, name: str, args: dict) -> str:
        async def work(s):
            return await s.call_tool(name, args)
        result = asyncio.run(self._with_session(work))
        text = "".join(getattr(c, "text", "") for c in result.content)
        if getattr(result, "isError", False) or getattr(result, "is_error", False):
            raise RuntimeError(text or f"tool {name} failed")
        return text

    def handlers(self, names: Optional[List[str]] = None) -> Dict[str, Callable]:
        def make(n):
            return lambda **kw: self.call(n, kw)
        return {t["name"]: make(t["name"]) for t in self.list_tools(names)}

