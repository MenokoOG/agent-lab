# m7 agent-org notes

- `whiteboard.md` lists capabilities, groups and the priority order.
- `compare.py --dry-run` runs 8 requests through the mega-agent and the team. The fake model makes no leaf calls, so wrong-tool counts are 0 for both. The real comparison needs `python compare.py` with a key.
- A2A vs MCP: MCP connects an agent to tools. A2A connects an agent to another agent that keeps its own model, memory and policy. I'd use A2A when the other agent belongs to a different team or vendor.
