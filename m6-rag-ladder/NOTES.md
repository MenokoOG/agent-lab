# m6 rag-ladder notes

- Built RAG by hand: `chunk`, TF-IDF vectors, cosine `top_k`, optional model `rerank`.
- `ladder.py --dry-run` runs all three rungs on 10 questions. The fake model scores 0/10 on purpose, so the dry run proves wiring only.
- Count and lookup questions ("total headcount", "locations above 25") are the ones retrieval can't answer from a chunk. Rung 2 tools read `offices.csv` directly.
- Which rung I'd ship: rung 2 for this corpus. 7 small files fit in one context, and the numeric questions need a tool. Confirm with `python ladder.py` on a live key before trusting that.
