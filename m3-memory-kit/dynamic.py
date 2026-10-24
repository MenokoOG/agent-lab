"""Dynamic agents: model, system prompt and tools chosen at runtime from user context."""

from dataclasses import dataclass


@dataclass
class AgentConfig:
    model: str
    system: str
    tool_names: list
    top_k: int


def config_for(user_tier: str, language: str) -> AgentConfig:
    if user_tier == "enterprise":
        return AgentConfig("claude-sonnet-5-5",
                           f"You are a priority support agent. Reply in {language}. Escalate to a human when unsure.",
                           ["search_docs", "lookup_account", "escalate"], top_k=15)
    if user_tier == "pro":
        return AgentConfig("claude-sonnet-5-5",
                           f"You give detailed technical support. Reply in {language}.",
                           ["search_docs", "lookup_account"], top_k=8)
    return AgentConfig("claude-haiku-5-5",
                       f"You give basic support and link to docs. Reply in {language}.",
                       ["search_docs"], top_k=8)


def pick_tools(cfg: AgentConfig, all_tools: list) -> list:
    """Hand the model only the tools this tier may use."""
    return [t for t in all_tools if t["name"] in cfg.tool_names]