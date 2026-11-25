"""Rung 1: put the whole corpus in the prompt. Simple and reliable until it isn't."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402
from corpus_io import load_docs  # noqa: E402


def answer(q: str) -> tuple:
    """Returns (answer text, input tokens)."""
    docs = "\n\n".join(f"--- {name} ---\n{text}" for name, text in load_docs().items())
    resp = llm.chat([{"role": "user", "content": f"Company files:\n{docs}\n\nQuestion: {q}\nAnswer briefly."}])
    return llm.text_of(resp), resp["usage"]["input_tokens"]
