"""Load the corpus folder: every .txt and .csv file becomes name -> text."""
import csv
import io
from pathlib import Path

CORPUS = Path(__file__).parent / "corpus"


def load_docs(folder=CORPUS) -> dict:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(folder.iterdir())
            if p.suffix in (".txt", ".csv")}


def office_rows(docs=None) -> list:
    docs = docs or load_docs()
    return list(csv.DictReader(io.StringIO(docs["offices.csv"])))
