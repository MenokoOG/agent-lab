"""Memory by hand. Every processor is a function from a message list to a message list."""

import json
import math
import re
from collections import Counter

def est_tokens(text: str) -> int:
    """Estimate the number of tokens in a string."""
    return max(1, len(text) // 4)  # rough: four characters per token

def msg_text(m: dict) -> str:
    """Get the text of a message."""
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

def window(messages: list, n: int) -> list:
    """Sliding window: the last n messages."""
    return messages[-n:] if n > 0 else []

def _words(text: str) -> list:
    return re.findall(r"[a-z0-9']+", text.lower())


def _tfidf(docs: list) -> list:
    df = Counter(w for d in docs for w in set(d))
    n = len(docs)
    vecs = []
    for d in docs:
        tf = Counter(d)
        vecs.append({w: c * (math.log((n + 1) / (df[w] + 1)) + 1) for w, c in tf.items()})
    return vecs, df, n


def _cosine(a: dict, b: dict) -> float:
    dot = sum(v * b.get(k, 0.0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def recall(query: str, history: list, k: int = 2, rng: int = 1) -> list:
    """Semantic-ish recall: TF-IDF similarity, top k hits, plus rng neighbours on each side."""
    if not history:
        return []
    docs = [_words(msg_text(m)) for m in history]
    vecs, df, n = _tfidf(docs)
    qtf = Counter(_words(query))
    qvec = {w: c * (math.log((n + 1) / (df.get(w, 0) + 1)) + 1) for w, c in qtf.items()}
    scored = sorted(((_cosine(qvec, v), i) for i, v in enumerate(vecs)), reverse=True)
    hits = [i for s, i in scored[:k] if s > 0]
    keep = sorted({j for i in hits for j in range(max(0, i - rng), min(len(history), i + rng + 1))})
    return [history[i] for i in keep]


def token_limiter(messages: list, limit: int) -> list:
    """Drop the oldest messages until the total fits under the limit."""
    out = list(messages)
    while out and sum(est_tokens(msg_text(m)) for m in out) > limit:
        out.pop(0)
    return out


def tool_call_filter(messages: list) -> list:
    """Remove tool calls and results so the agent calls a tool again instead of trusting an old one."""
    out = []
    for m in messages:
        if isinstance(m["content"], str):
            out.append(m)
            continue
        blocks = [b for b in m["content"] if b["type"] == "text"]
        if blocks:
            out.append({"role": m["role"], "content": blocks})
    return out


def build_context(history: list, query: str, last_n: int = 6, top_k: int = 2,
                  rng: int = 1, limit: int = 2000) -> list:
    """Recent window + recalled old messages, filtered and trimmed, then the new question."""
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