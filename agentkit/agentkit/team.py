"""m7: specialists, agents as tools, a one-call router and a supervisor.

route() is the cheap path: one model call picks a specialist by name. supervisor() is the flexible
path: a router agent that can call several specialists, each wrapped as a tool.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from agentkit import llm
from agentkit.loop import Result, run_agent
from agentkit.prompts import pick_label


@dataclass
class Specialist:
    name: str
    description: str  # what the router reads to choose
    system: str
    tools: List[dict] = field(default_factory=list)
    handlers: Dict[str, Callable] = field(default_factory=dict)
    max_steps: int = 6

    def run(self, goal, model: Optional[str] = None) -> Result:
        return run_agent(goal, self.tools, self.handlers, system=self.system,
                         max_steps=self.max_steps, model=model)


def agent_as_tool(s: Specialist) -> Tuple[dict, Callable[..., str]]:
    schema = {"type": "object", "properties": {"brief": {"type": "string", "description": "The full request"}},
              "required": ["brief"]}

    def handler(brief: str) -> str:
        return s.run(brief).answer

    return {"name": f"ask_{s.name}", "description": s.description, "input_schema": schema}, handler


def route(request: str, specialists: List[Specialist], default: Optional[str] = None) -> str:
    """One model call. Returns a specialist name; an unparseable reply falls back to default."""
    if not specialists:
        raise ValueError("route needs at least one specialist")
    names = [s.name for s in specialists]
    menu = "\n".join(f"- {s.name}: {s.description}" for s in specialists)
    reply = llm.ask(f"Pick the one specialist for this request. Reply with only its name.\n\n"
                    f"Specialists:\n{menu}\n\nRequest: {request}", model=llm.SMALL_MODEL, max_tokens=10)
    return pick_label(reply, names, default or names[0])


def supervisor(request: str, specialists: List[Specialist], system: str = "") -> Result:
    tools: List[dict] = []
    handlers: Dict[str, Callable[..., object]] = {}
    for s in specialists:
        tool, fn = agent_as_tool(s)
        tools.append(tool)
        handlers[tool["name"]] = fn
    return run_agent(request, tools, handlers,
                     system=system or "You route requests to the right specialist, then answer. Be brief.")
