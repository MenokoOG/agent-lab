"""m3: dynamic agents. Model, system prompt, tools and limits chosen at runtime from user context."""
from dataclasses import dataclass
from typing import Dict, List

from agentkit import llm


@dataclass(frozen=True)
class AgentConfig:
    tier: str
    model: str
    system: str
    allowed_tools: List[str]
    top_k: int
    memory_limit: int


_TIERS: Dict[str, dict] = {
    "enterprise": {"model": llm.MODEL, "style": "You are a priority support agent. Escalate to a human when unsure.",
                   "tools": ["lookup_order", "search_policy", "escalate"], "top_k": 4, "memory_limit": 4000},
    "pro": {"model": llm.MODEL, "style": "You give detailed support.",
            "tools": ["lookup_order", "search_policy"], "top_k": 3, "memory_limit": 2500},
    "free": {"model": llm.SMALL_MODEL, "style": "You give short support answers and point to the policy.",
             "tools": ["search_policy"], "top_k": 2, "memory_limit": 1500},
}


def config_for(user_tier: str, language: str = "English") -> AgentConfig:
    t = _TIERS.get(user_tier, _TIERS["free"])  # unknown tiers get the least access, never the most
    return AgentConfig(user_tier if user_tier in _TIERS else "free", t["model"],
                       f"{t['style']} Reply in {language}.", list(t["tools"]), t["top_k"], t["memory_limit"])


def pick_tools(cfg: AgentConfig, all_tools: List[dict]) -> List[dict]:
    """Hand the model only the tools this tier may use."""
    return [t for t in all_tools if t["name"] in cfg.allowed_tools]
