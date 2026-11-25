"""m3: memory by hand. Every processor is a function from a message list to a message list."""
import json
import math
import re
from collections import Counter
from typing import Dict, List, Tuple


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # rough: four characters per token


def msg_text(m: dict) -> str:
    c = m["content"]
    if isinstance(c, str):
        return c
    parts = []
    for b in c:
        if b["type"] == "text":
            parts.append(b["text"])
        elif b["type"] == "tool_use":
            parts.append(json.dumps(b["input"]))
        elif b["type"] == "tool_result":
            parts.append(str(b["content"]))
    return " ".join(parts)


def window(messages: List[dict], n: int) -> List[dict]:
    return messages[-n:] if n > 0 else []


def _words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _idf(docs: List[List[str]]) -> Tuple[Dict[str, float], int]:
    df = Counter(w for d in docs for w in set(d))
    n = len(docs)
    return {w: math.log((n + 1) / (c + 1)) + 1 for w, c in df.items()}, n


def _vec(words: List[str], idf: Dict[str, float], n: int) -> Dict[str, float]:
    default = math.log(n + 1) + 1  # unseen word: df of 0
    return {w: c * idf.get(w, default) for w, c in Counter(words).items()}


def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def recall(query: str, history: List[dict], k: int = 2, rng: int = 1) -> List[dict]:
    """TF-IDF similarity, top k hits, plus rng neighbours on each side so a hit keeps its context."""
    if not history:
        return []
    docs = [_words(msg_text(m)) for m in history]
    idf, n = _idf(docs)
    vecs = [_vec(d, idf, n) for d in docs]
    q = _vec(_words(query), idf, n)
    scored = sorted(((cosine(q, v), i) for i, v in enumerate(vecs)), reverse=True)
    hits = [i for s, i in scored[:k] if s > 0]
    keep = sorted({j for i in hits for j in range(max(0, i - rng), min(len(history), i + rng + 1))})
    return [history[i] for i in keep]


def token_limiter(messages: List[dict], limit: int) -> List[dict]:
    out = list(messages)
    while out and sum(est_tokens(msg_text(m)) for m in out) > limit:
        out.pop(0)
    return out


def tool_call_filter(messages: List[dict]) -> List[dict]:
    """Drop tool calls and results so the agent calls a tool again instead of trusting an old answer."""
    out = []
    for m in messages:
        if isinstance(m["content"], str):
            out.append(m)
            continue
        blocks = [b for b in m["content"] if b["type"] == "text"]
        if blocks:
            out.append({"role": m["role"], "content": blocks})
    return out


def build_context(history: List[dict], query: str, last_n: int = 6, top_k: int = 2,
                  rng: int = 1, limit: int = 2000) -> List[dict]:
    """Recent window plus recalled older messages, filtered and trimmed, then the new question."""
    budget = limit - est_tokens(query)
    if budget <= 0:
        raise ValueError("the query alone exceeds the token limit")
    recent = window(history, last_n)
    older = history[:len(history) - len(recent)]
    pool = recall(query, older, top_k, rng) + recent
    pool = token_limiter(tool_call_filter(pool), budget)
    while pool and pool[0]["role"] != "user":  # the API wants the first message to be a user turn
        pool.pop(0)
    return pool + [{"role": "user", "content": query}]
