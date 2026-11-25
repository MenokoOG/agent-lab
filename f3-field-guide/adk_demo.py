"""Google ADK (Agent Development Kit): code-first agents with a built-in dev UI (adk web) and Vertex AI deploy.

    pip install google-adk litellm
    python adk_demo.py           # Claude through LiteLLM (needs ANTHROPIC_API_KEY)
"""
import asyncio

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types

from shared import INSTRUCTIONS, MODEL, QUESTION, count_by


def build() -> Agent:
    # Plain functions become tools. ADK reads the docstring. A Gemini model id string also works here.
    return Agent(name="book_analyst", model=LiteLlm(model=f"anthropic/{MODEL}"),
                 instruction=INSTRUCTIONS, tools=[count_by])


async def ask(question: str) -> str:
    runner = InMemoryRunner(agent=build(), app_name="field_guide")
    session = await runner.session_service.create_session(app_name="field_guide", user_id="me")
    final = ""
    async for event in runner.run_async(user_id="me", session_id=session.id,
                                        new_message=types.Content(role="user", parts=[types.Part(text=question)])):
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(p.text or "" for p in event.content.parts)
    return final


if __name__ == "__main__":
    print(asyncio.run(ask(QUESTION)))
