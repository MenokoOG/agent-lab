"""OpenAI Agents SDK: small core of Agent, Runner, handoffs and guardrails.

    pip install "openai-agents[litellm]"
    python openai_agents_demo.py                # uses Claude through LiteLLM (needs ANTHROPIC_API_KEY)
    USE_OPENAI=1 python openai_agents_demo.py   # uses an OpenAI model (needs OPENAI_API_KEY)
"""
import os

from agents import Agent, Runner, function_tool

from shared import INSTRUCTIONS, MODEL, QUESTION, count_by


def build() -> Agent:
    model = None  # None means the SDK's default OpenAI model
    if not os.environ.get("USE_OPENAI"):
        from agents.extensions.models.litellm_model import LitellmModel
        model = LitellmModel(model=f"anthropic/{MODEL}")
    kwargs = {"model": model} if model else {}
    return Agent(name="book_analyst", instructions=INSTRUCTIONS, tools=[function_tool(count_by)], **kwargs)


if __name__ == "__main__":
    result = Runner.run_sync(build(), QUESTION)
    print(result.final_output)
