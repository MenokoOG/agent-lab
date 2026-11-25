"""The one task every demo solves, and the one tool they all get. Reuses module 2's corpus."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))
import tools as books  # noqa: E402

QUESTION = "Which genre has the most books, and how many does it have?"
INSTRUCTIONS = "You analyze a book corpus. Use the count_by tool for any counting question. Answer in one sentence."
MODEL = "claude-sonnet-5-5"


def count_by(field: str) -> str:
    """Count books grouped by genre, recommender or author. Call for any how-many, most or least question.

    Args:
        field: One of genre, recommender, author.
    """
    return books.count_by(field)
