"""Module 2's book analyst, rebuilt with Strands Agents.

    python book_agent.py "Which genre has the most books?"

What disappeared compared with your loop.py: the for-loop, the stop_reason check, the tool_result
messages and the hand-written JSON schemas. Strands builds the schema from the type hints and the
docstring's Args section, so the docstring is now the tool description the model reads.
"""
import sys
from pathlib import Path

from strands import Agent, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager

sys.path.append(str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))
import tools as books  # noqa: E402  (module 2's pure functions)

SYSTEM = "You analyze a book corpus. Use the tools for counts and lists. Answer briefly."


@tool
def list_genres() -> str:
    """List every genre in the book corpus. Call this first when the user asks about categories."""
    return books.list_genres()


@tool
def books_by_genre(genre: str) -> str:
    """List the books (title and author) in one genre. Call when asked what is in a genre or who wrote a book.

    Args:
        genre: A genre name from list_genres.
    """
    return books.books_by_genre(genre)


@tool
def recs_by_person(person: str) -> str:
    """List the titles one person recommended. Call when asked what a named person recommended.

    Args:
        person: The recommender's first name.
    """
    return books.recs_by_person(person)


@tool
def count_by(field: str) -> str:
    """Count books grouped by genre, recommender or author. Call for any how-many, most or least question.

    Args:
        field: One of genre, recommender, author.
    """
    return books.count_by(field)


TOOLS = [list_genres, books_by_genre, recs_by_person, count_by]


def build_agent(model=None) -> Agent:
    if model is None:
        from models import make_model
        model = make_model()
    return Agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM,
        # module 3's sliding window, built in: keep the last 20 messages
        conversation_manager=SlidingWindowConversationManager(window_size=20),
        callback_handler=None,  # no streaming to the terminal; we print the result ourselves
    )


if __name__ == "__main__":
    agent = build_agent()
    result = agent(" ".join(sys.argv[1:]) or "Which genre has the most books?")
    print(str(result).strip())
    print(f"[tools used: {list(result.metrics.tool_metrics)}]")
