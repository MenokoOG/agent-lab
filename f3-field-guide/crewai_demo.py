"""CrewAI: role-based agents and tasks. You describe a team (role, goal, backstory) and the work.

    pip install "crewai[anthropic]"
    python crewai_demo.py
"""
from crewai import LLM, Agent, Crew, Task
from crewai.tools import tool

from shared import MODEL, QUESTION, count_by


@tool("count_by")
def count_by_tool(field: str) -> str:
    """Count books grouped by genre, recommender or author. Call for any how-many, most or least question."""
    return count_by(field)


def build() -> Crew:
    analyst = Agent(
        role="Book analyst",
        goal="Answer questions about the book corpus with exact numbers",
        backstory="You never guess a count. You always use your tool.",
        tools=[count_by_tool],
        llm=LLM(model=f"anthropic/{MODEL}"),
    )
    task = Task(description=QUESTION, expected_output="One sentence with the genre and its count.", agent=analyst)
    return Crew(agents=[analyst], tasks=[task])


if __name__ == "__main__":
    print(build().kickoff())
