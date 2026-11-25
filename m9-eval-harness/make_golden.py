"""Generate golden.csv from the module 2 corpus, so every reference answer is computed, not typed.

Course note: the course says to write 30 pairs yourself. Do that for your own agent. This generator
exists so the reference build has a correct golden set to run against. Re-run after changing the corpus.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))
import tools  # noqa: E402

OUT = Path(__file__).parent / "golden.csv"


def build_rows(rows):
    by_genre = Counter(r["genre"] for r in rows)
    by_rec = Counter(r["recommender"] for r in rows)
    out = []

    def add(question, reference, tag, expected_tools):
        out.append({"id": f"g{len(out) + 1:02d}", "question": question, "reference": reference,
                    "tag": tag, "expected_tools": "|".join(expected_tools)})

    for genre, n in by_genre.items():
        add(f"How many books are in the {genre} genre?", f"{n} books.", "count", ["count_by"])
    for rec, n in by_rec.items():
        add(f"How many books did {rec} recommend?", f"{n} books.", "count", ["count_by", "recs_by_person"])
    for rec in by_rec:
        titles = [r["title"] for r in rows if r["recommender"] == rec]
        add(f"Which books did {rec} recommend?", "; ".join(titles), "list", ["recs_by_person"])
    for genre in by_genre:
        titles = [r["title"] for r in rows if r["genre"] == genre]
        add(f"List the books in the {genre} genre.", "; ".join(titles), "list", ["books_by_genre"])
    for genre in by_genre:
        r = next(r for r in rows if r["genre"] == genre)
        add(f"Who wrote {r['title']}?", r["author"], "lookup", ["books_by_genre"])
    top_genre, top_rec = by_genre.most_common(1)[0][0], by_rec.most_common(1)[0][0]
    add("How many books are in the corpus in total?", f"{len(rows)} books.", "aggregate", ["count_by"])
    add("Which genre has the most books?", top_genre, "aggregate", ["count_by"])
    add("Which person recommended the most books?", top_rec, "aggregate", ["count_by"])
    add("How many different genres are there?", f"{len(by_genre)} genres.", "aggregate", ["list_genres", "count_by"])
    add("How many different people made recommendations?", f"{len(by_rec)} people.", "aggregate", ["count_by"])
    return out


if __name__ == "__main__":
    rows = build_rows(tools.ROWS)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "question", "reference", "tag", "expected_tools"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT.name}: {json.dumps(Counter(r['tag'] for r in rows))}")
