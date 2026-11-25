"""m6: RAG by hand. Chunk, vectorize (TF-IDF), cosine top k, optional model rerank."""
import re
from typing import Dict, List, Tuple

from agentkit import llm
from agentkit.memory import _idf, _vec, cosine

Hit = Tuple[str, str]  # (doc name, chunk text)


def chunk(text: str, size: int = 200, overlap: int = 40) -> List[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    step = size - overlap
    return [text[i:i + size] for i in range(0, max(len(text), 1), step) if text[i:i + size].strip()]


def words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9$']+", text.lower())


class Index:
    def __init__(self, docs: Dict[str, str], size: int = 200, overlap: int = 40) -> None:
        self.chunks: List[Hit] = [(name, c) for name, text in docs.items() for c in chunk(text, size, overlap)]
        toks = [words(c) for _, c in self.chunks]
        self.idf, self.n = _idf(toks)
        self.vecs = [_vec(t, self.idf, self.n) for t in toks]

    def top_k(self, query: str, k: int = 3) -> List[Hit]:
        q = {w: v for w, v in _vec(words(query), self.idf, self.n).items() if w in self.idf}
        scored = sorted(((cosine(q, v), i) for i, v in enumerate(self.vecs)), reverse=True)
        return [self.chunks[i] for s, i in scored[:k] if s > 0]


def rerank(question: str, hits: List[Hit]) -> List[Hit]:
    """Ask the model to order the candidates. Unparseable replies fall back to the original order."""
    if len(hits) < 2:
        return hits
    listing = "\n".join(f"[{i}] {c}" for i, (_, c) in enumerate(hits))
    reply = llm.ask(f"Question: {question}\n\nPassages:\n{listing}\n\n"
                    "List the passage numbers from most to least useful, comma separated, numbers only.",
                    model=llm.SMALL_MODEL, max_tokens=20)
    order = [int(x) for x in re.findall(r"\d+", reply) if int(x) < len(hits)]
    seen, ranked = set(), []
    for i in order + list(range(len(hits))):
        if i not in seen:
            seen.add(i)
            ranked.append(hits[i])
    return ranked


def format_hits(hits: List[Hit]) -> str:
    return "\n\n".join(f"[{name}] {c}" for name, c in hits) or "no matching passages"
