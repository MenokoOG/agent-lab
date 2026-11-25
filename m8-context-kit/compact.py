"""Compaction: when the context passes a threshold, summarize the old part and keep the recent part."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402


def est_tokens(messages: list) -> int:
    return sum(max(1, len(json.dumps(m["content"])) // 4) for m in messages)


def llm_summarize(old: list) -> str:
    text = "\n".join(f"{m['role']}: {m['content'] if isinstance(m['content'], str) else json.dumps(m['content'])}"
                     for m in old)
    return llm.ask("Summarize this conversation so work can continue. Keep names, numbers and open questions. "
                   f"Be short.\n\n{text}", max_tokens=500)


def compact(messages: list, threshold: int, keep_last: int = 4, must_keep=(), summarize=llm_summarize) -> list:
    """Below the threshold, return the messages untouched. Above it, replace everything but the last
    keep_last messages with one summary message. must_keep lines are copied in verbatim, because a
    summary drops detail by design."""
    if est_tokens(messages) <= threshold or len(messages) <= keep_last:
        return messages
    old, recent = messages[:-keep_last], messages[-keep_last:]
    kept = "\n".join(f"- {d}" for d in must_keep)
    note = f"Summary of earlier work:\n{summarize(old)}\n\nDecisions to keep verbatim:\n{kept or '- none'}"
    # Two user messages in a row are fine: the API merges consecutive turns with the same role.
    return [{"role": "user", "content": note}] + recent
