"""Rung 3: RAG by hand. Chunk, vectorize (TF-IDF), cosine top K, optional rerank, synthesize."""
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402
from corpus_io import load_docs  # noqa: E402


def chunk(text: str, size: int = 200, overlap: int = 40) -> list:
    step = size - overlap
    return [text[i:i + size] for i in range(0, max(len(text), 1), step) if text[i:i + size].strip()]


def words(text: str) -> list:
    return re.findall(r"[a-z0-9$']+", text.lower())


def cosine(a: dict, b: dict) -> float:
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na, nb = math.sqrt(sum(v * v for v in a.values())), math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


class Index:
    def __init__(self, docs: dict, size: int = 200, overlap: int = 40):
        self.chunks = [(name, c) for name, text in docs.items() for c in chunk(text, size, overlap)]
        toks = [words(c) for _, c in self.chunks]
        n = len(toks)
        df = Counter(w for t in toks for w in set(t))
        self.idf = {w: math.log((n + 1) / (d + 1)) + 1 for w, d in df.items()}
        self.vecs = [self._vec(t) for t in toks]

    def _vec(self, toks):
        return {w: c * self.idf.get(w, 0.0) for w, c in Counter(toks).items()}

    def top_k(self, query: str, k: int = 3) -> list:
        qv = self._vec(words(query))
        scored = sorted(((cosine(qv, v), i) for i, v in enumerate(self.vecs)), reverse=True)
        return [self.chunks[i] for s, i in scored[:k] if s > 0]


def rerank(question: str, hits: list) -> list:
    """Optional: ask the model to order the candidates. Falls back to the original order."""
    listing = "\n".join(f"[{i}] {c}" for i, (_, c) in enumerate(hits))
    reply = llm.ask(f"Question: {question}\n\nPassages:\n{listing}\n\n"
                    "List the passage numbers from most to least useful, comma separated, numbers only.", max_tokens=20)
    order = [int(x) for x in re.findall(r"\d+", reply) if int(x) < len(hits)]
    seen, ranked = set(), []
    for i in order + list(range(len(hits))):
        if i not in seen:
            seen.add(i)
            ranked.append(hits[i])
    return ranked


_INDEX = None


def answer(q: str, k: int = 3, use_rerank: bool = False) -> tuple:
    global _INDEX
    _INDEX = _INDEX or Index(load_docs())
    hits = _INDEX.top_k(q, k + 2 if use_rerank else k)
    if use_rerank and hits:
        hits = rerank(q, hits)[:k]
    context = "\n\n".join(f"[{name}] {c}" for name, c in hits)
    resp = llm.chat([{"role": "user", "content": f"Use only these passages.\n\n{context}\n\nQuestion: {q}\nAnswer briefly."}])
    return llm.text_of(resp), resp["usage"]["input_tokens"]
