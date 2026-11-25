"""A router plus specialists. Each specialist is an agent wrapped as a tool the router can call."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))  # append, so local names win
from loop import run_agent  # noqa: E402
from shop import CATALOG_TOOLS, LEAF_HANDLERS, ORDER_TOOLS, logged  # noqa: E402


def agent_as_tool(name, description, system, tools, handlers):
    schema = {"type": "object", "properties": {"brief": {"type": "string"}}, "required": ["brief"]}

    def handler(brief):
        return run_agent(brief, tools, handlers, system=system).answer

    return {"name": name, "description": description, "input_schema": schema}, handler


# Adding a specialist later (the "evolve" step) means adding one row here.
SPECIALISTS = [
    {"name": "ask_orders", "tools": ORDER_TOOLS,
     "description": "Order questions: status, history, what a customer bought. Pass the full request as the brief.",
     "system": "You answer order questions using your tools. Be brief."},
    {"name": "ask_catalog", "tools": CATALOG_TOOLS,
     "description": "Product questions: what we sell, stock, availability. Pass the full request as the brief.",
     "system": "You answer product and stock questions using your tools. Be brief."},
]


def ask(request: str, log: list) -> str:
    handlers = logged(LEAF_HANDLERS, log)
    router_tools, router_handlers = [], {}
    for s in SPECIALISTS:
        tool, fn = agent_as_tool(s["name"], s["description"], s["system"], s["tools"],
                                 {t["name"]: handlers[t["name"]] for t in s["tools"]})
        router_tools.append(tool)
        router_handlers[s["name"]] = fn
    return run_agent(request, router_tools, router_handlers,
                     system="You route shop requests to the right specialist, then answer. Be brief.").answer
