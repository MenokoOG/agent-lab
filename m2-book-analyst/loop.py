"""The agent loop: a model, some tools, a bounded loop. Errors are surfaced, never swallowed."""
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402


@dataclass
class Result:
    answer: str
    steps: int
    input_tokens: int
    tool_calls: list = field(default_factory=list)


def run_agent(goal, tools, handlers, system="", max_steps=8, model=None) -> Result:
    """goal is a string, or a ready-made message list (module 3 builds one)."""
    messages = [{"role": "user", "content": goal}] if isinstance(goal, str) else list(goal)
    steps, tokens, calls = 0, 0, []
    for _ in range(max_steps):
        resp = llm.chat(messages, system=system, tools=tools, model=model)
        steps += 1
        tokens += resp["usage"]["input_tokens"]
        messages.append({"role": "assistant", "content": resp["content"]})
        if resp["stop_reason"] != "tool_use":
            return Result(llm.text_of(resp), steps, tokens, calls)
        results = []
        for block in resp["content"]:
            if block["type"] != "tool_use":
                continue
            calls.append(block["name"])
            try:
                out, err = handlers[block["name"]](**block["input"]), False
            except Exception as e:  # surface errors to the model, never swallow
                out, err = f"error: {e}", True
            results.append({"type": "tool_result", "tool_use_id": block["id"],
                            "content": str(out), "is_error": err})
        messages.append({"role": "user", "content": results})
    raise RuntimeError("step budget exhausted")