"""The hand-built tool registry: what MCP standardizes. Reuses the module 2 corpus functions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))
import tools as books  # noqa: E402

REGISTRY = {}


def tool(description, schema):
    def wrap(fn):
        REGISTRY[fn.__name__] = {"fn": fn, "description": description, "schema": schema}
        return fn
    return wrap


def _one(name, desc):
    return {"type": "object", "properties": {name: {"type": "string", "description": desc}}, "required": [name]}


@tool("List every genre in the book corpus. Call first when the user asks about categories.",
      {"type": "object", "properties": {}})
def list_genres() -> str:
    return books.list_genres()


@tool("List the books (title and author) in one genre. Call when asked what is in a genre or who wrote a book.",
      _one("genre", "A genre name from list_genres"))
def books_by_genre(genre: str) -> str:
    return books.books_by_genre(genre)


@tool("List the titles one person recommended. Call when asked what a named person recommended.",
      _one("person", "The recommender's first name"))
def recs_by_person(person: str) -> str:
    return books.recs_by_person(person)


@tool("Count books grouped by genre, recommender or author. Call for any how-many, most or least question.",
      _one("field", "One of: genre, recommender, author"))
def count_by(field: str) -> str:
    return books.count_by(field)


def list_tools():
    """What a client asks a server for."""
    return [{"name": n, "description": t["description"], "input_schema": t["schema"]}
            for n, t in REGISTRY.items()]


def handlers():
    return {n: t["fn"] for n, t in REGISTRY.items()}


def call_tool(name, args):
    """What a client asks a server to run."""
    return REGISTRY[name]["fn"](**args)
