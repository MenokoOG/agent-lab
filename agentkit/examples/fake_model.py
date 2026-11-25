"""A scripted stand-in for the model, shaped like the real API. Used by tests and --dry-run.

It answers by reading the prompt the way a careful model would, so the plumbing runs end to end.
The numbers it produces measure wiring, not model quality.
"""
import json
import re

from agentkit import llm


def _last_user(body: dict):
    for m in reversed(body["messages"]):
        if m["role"] == "user":
            return m["content"]
    return ""


def _first_user_text(body: dict) -> str:
    """The request a specialist is working on: the newest plain-text user turn."""
    for m in reversed(body["messages"]):
        if m["role"] == "user" and isinstance(m["content"], str):
            return m["content"]
    return ""


def desk_fake(body: dict) -> dict:
    last = _last_user(body)
    if isinstance(last, list):  # tool results came back: answer from them
        results = " ".join(str(b.get("content", "")) for b in last if b.get("type") == "tool_result")
        return llm.fake_text(f"Here is what I found: {results}")
    text = last
    lower = text.lower()
    if "pick the one specialist" in lower:
        req = text.split("Request:", 1)[-1].lower()
        return llm.fake_text("orders" if re.search(r"\b\d{4}\b|order", req) else "policy")
    if "answer yes or no" in lower:
        msg = text.split("Message:", 1)[-1].lower()
        if "today" in text.split("Message:")[0].lower():
            return llm.fake_text("yes" if re.search(r"today|asap|urgent|now", msg) else "no")
        return llm.fake_text("yes" if re.search(r"refund|money back|charged twice", msg) else "no")
    if lower.startswith("summarize this conversation"):
        return llm.fake_text("Earlier: the customer asked about orders and policy.")
    if "you grade an answer" in lower:
        found = re.search(r"Reference: (.*)\n", text)
        ref = found.group(1).lower() if found else "\0"  # no reference line: nothing can match
        ans = text.split("Answer:", 1)[-1].lower()
        return llm.fake_text("PASS" if ref in ans else "FAIL")
    tools = {t["name"] for t in body.get("tools") or []}
    request = _first_user_text(body)
    order = re.search(r"\b(\d{4})\b", request)
    if order and "lookup_order" in tools:
        return llm.fake_tool_use("lookup_order", {"order_id": order.group(1)})
    if "search_policy" in tools:
        return llm.fake_tool_use("search_policy", {"query": request[:80]})
    if "escalate" in tools:
        return llm.fake_tool_use("escalate", {"reason": "no tool for this on the current plan"})
    return llm.fake_text("I can't look that up on your plan. " + json.dumps({"tools": sorted(tools)}))
