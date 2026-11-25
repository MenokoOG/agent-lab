"""Rung 2: write functions over the dataset and give them to an agent (reuses module 2's loop)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))
from corpus_io import load_docs, office_rows  # noqa: E402
from loop import run_agent  # noqa: E402

DOCS = load_docs()
ROWS = office_rows(DOCS)


def list_docs():
    return json.dumps([n for n in DOCS if n.endswith(".txt")])


def read_doc(name):
    return DOCS[name]


def total_headcount():
    return str(sum(int(r["headcount"]) for r in ROWS))


def largest_location():
    top = max(ROWS, key=lambda r: int(r["headcount"]))
    return f"{top['location']} ({top['headcount']})"


def locations_above(n):
    return json.dumps([r["location"] for r in ROWS if int(r["headcount"]) > int(n)])


def _schema(**props):
    return {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props)}


TOOLS = [
    {"name": "list_docs", "description": "List policy document names. Call first for any policy question.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_doc", "description": "Read one policy document by file name. Call after list_docs to find a policy fact.",
     "input_schema": _schema(name="A file name from list_docs, such as security.txt")},
    {"name": "total_headcount", "description": "Total employees across every location. Call for any company-wide headcount question.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "largest_location", "description": "The location with the most people. Call for which-office-is-biggest questions.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "locations_above", "description": "Locations whose headcount is above a number. Call for how-many-locations-exceed questions.",
     "input_schema": _schema(n="The headcount threshold as a number")},
]
HANDLERS = {"list_docs": list_docs, "read_doc": read_doc, "total_headcount": total_headcount,
            "largest_location": largest_location, "locations_above": locations_above}


def answer(q: str) -> tuple:
    try:
        r = run_agent(q, TOOLS, HANDLERS, system="Answer company questions using the tools. Be brief.")
        return r.answer, r.input_tokens
    except RuntimeError as e:
        return f"[{e}]", 0
