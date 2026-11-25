"""A scripted Strands model for offline tests. It speaks the same stream events a real provider does.

Each scripted turn is either a string (the model answers) or a ("tool", name, args) tuple (the model calls a tool).
"""
import json
from typing import Any

from strands.models.model import Model


class ScriptedModel(Model):
    def __init__(self, *turns):
        self.turns = list(turns)
        self.requests = []  # what the agent sent on each call: messages, tool names, system prompt

    def update_config(self, **model_config: Any) -> None:
        pass

    def get_config(self) -> dict:
        return {"model_id": "scripted"}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError("not needed for these lessons")
        yield  # pragma: no cover

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.requests.append({"messages": list(messages),
                              "tools": [t["name"] for t in (tool_specs or [])],
                              "system": system_prompt})
        if not self.turns:
            raise RuntimeError("ScriptedModel ran out of turns")
        turn = self.turns.pop(0)
        yield {"messageStart": {"role": "assistant"}}
        if isinstance(turn, tuple):
            _, name, args = turn
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"t{len(self.requests)}", "name": name}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(args)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": turn}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        yield {"metadata": {"usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                            "metrics": {"latencyMs": 0}}}
