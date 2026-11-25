"""LLM judge: binary PASS or FAIL against a reference. Binary beats 1-to-10 because models grade words better than numbers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402

JUDGE = """You grade an answer against a reference. Reply with exactly PASS or FAIL.
Criteria: {criteria}
Question: {q}
Reference: {ref}
Answer: {ans}"""

DEFAULT_CRITERIA = ("The answer states the same facts as the reference. Extra correct detail is fine. "
                    "Any missing item from a list, or any wrong number or name, is a FAIL.")


def judge(q: str, ref: str, ans: str, criteria: str = DEFAULT_CRITERIA) -> bool:
    reply = llm.ask(JUDGE.format(criteria=criteria, q=q, ref=ref, ans=ans), max_tokens=5)
    return reply.strip().upper().startswith("PASS")


def agreement(judged: dict, hand: dict) -> tuple:
    """Compare judge results with your own grades. Both map id -> bool. Returns (n, agreeing, disagreeing ids)."""
    shared = [i for i in hand if i in judged]
    bad = [i for i in shared if judged[i] != hand[i]]
    return len(shared), len(shared) - len(bad), bad
