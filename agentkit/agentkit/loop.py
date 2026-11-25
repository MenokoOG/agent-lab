"""m2: the agent loop. A model, some tools, a bounded loop. Errors are surfaced, never swallowed."""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Union

from agentkit import llm

Handlers = Dict[str, Callable[..., object]]


class StepBudgetExhausted(RuntimeError):
    """The model kept calling tools past max_steps."""


@dataclass
class Result:
    answer: str
    steps: int
    input_tokens: int
    tool_calls: List[str] = field(default_factory=list)
    messages: List[dict] = field(default_factory=list)


def run_agent(goal: Union[str, List[dict]], tools: List[dict], handlers: Handlers, *, system: str = "",
              max_steps: int = 8, model: Optional[str] = None) -> Result:
    """goal is a string, or a ready-made message list (memory.build_context makes one)."""
    messages: List[dict] = [{"role": "user", "content": goal}] if isinstance(goal, str) else list(goal)
    steps, tokens = 0, 0
    calls: List[str] = []
    for _ in range(max_steps):
        resp = llm.chat(messages, system=system, tools=tools or None, model=model)
        steps += 1
        tokens += resp["usage"]["input_tokens"]
        messages.append({"role": "assistant", "content": resp["content"]})
        if resp["stop_reason"] != "tool_use":
            return Result(llm.text_of(resp), steps, tokens, calls, messages)
        results: List[dict] = []
        for block in resp["content"]:
            if block["type"] != "tool_use":
                continue
            calls.append(block["name"])
            handler = handlers.get(block["name"])
            try:
                if handler is None:
                    raise KeyError(f"unknown tool {block['name']}")
                out, err = handler(**block["input"]), False
            except Exception as e:  # surface errors to the model, never swallow
                out, err = f"error: {e}", True
            results.append({"type": "tool_result", "tool_use_id": block["id"],
                            "content": str(out), "is_error": err})
        messages.append({"role": "user", "content": results})
    raise StepBudgetExhausted(f"step budget of {max_steps} exhausted; tools called: {calls}")
