"""Pydantic AI: typed output and dependency injection. The best offline testing story of the group.

    pip install "pydantic-ai-slim[anthropic]"
    python pydantic_ai_demo.py
"""
from pydantic import BaseModel
from pydantic_ai import Agent

from shared import INSTRUCTIONS, MODEL, QUESTION, count_by


class Answer(BaseModel):
    genre: str
    count: int


def build(model=f"anthropic:{MODEL}") -> Agent:
    # output_type makes the agent return a validated Answer, not a string.
    return Agent(model, instructions=INSTRUCTIONS, tools=[count_by], output_type=Answer)


if __name__ == "__main__":
    result = build().run_sync(QUESTION)
    print(result.output)  # Answer(genre='sci-fi', count=8) if the model gets it right
