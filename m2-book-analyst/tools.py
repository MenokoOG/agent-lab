"""Pure functions over the corpus, plus the schemas the model sees."""
import csv
import json
from collections import Counter
from pathlib import Path

BOOKS = Path(__file__).parent / "books.csv"
FIELDS = ["genre", "recommender", "author"]


def load(path=BOOKS):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


ROWS = load()


def list_genres():
    return json.dumps(sorted({r["genre"] for r in ROWS}))


def books_by_genre(genre):
    hits = [f"{r['title']} by {r['author']}" for r in ROWS if r["genre"].lower() == genre.lower()]
    return json.dumps(hits)


def recs_by_person(person):
    hits = [r["title"] for r in ROWS if r["recommender"].lower() == person.lower()]
    return json.dumps(hits)


def count_by(field):
    if field not in FIELDS:
        raise ValueError(f"field must be one of {FIELDS}")
    return json.dumps(dict(Counter(r[field] for r in ROWS)))


def _schema(**props):
    return {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props)}


TOOLS = [
    {"name": "list_genres",
     "description": "List every genre in the book corpus. Call this first when the user asks about categories or genre names.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "books_by_genre",
     "description": "List the books (title and author) in one genre. Call when asked what is in a genre or who wrote a book.",
     "input_schema": _schema(genre="A genre name from list_genres")},
    {"name": "recs_by_person",
     "description": "List the titles one person recommended. Call when asked what a named person recommended.",
     "input_schema": _schema(person="The recommender's first name")},
    {"name": "count_by",
     "description": "Count books grouped by genre, recommender or author. Call for any how-many, most or least question.",
     "input_schema": _schema(field="One of: genre, recommender, author")},
]

HANDLERS = {"list_genres": list_genres, "books_by_genre": books_by_genre,
            "recs_by_person": recs_by_person, "count_by": count_by}