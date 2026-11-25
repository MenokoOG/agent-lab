"""Module 5's triage workflow, rebuilt in LangGraph.

    python triage_graph.py "I was charged twice. Fix it today."   # runs until the approval interrupt
    python triage_graph.py --resume THREAD_ID yes                   # picks up where it stopped

State lives in runs.sqlite, so you can close the terminal between the two commands.
Every node makes at most one LLM call, through the same llm.py the hand-built modules use.
"""
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402

DB = Path(__file__).parent / "runs.sqlite"


class Triage(TypedDict, total=False):
    email: str
    category: str
    urgent: bool
    angry: bool
    refund: bool
    flags: list
    priority: str
    approved: str
    reply: str


def _yes(question: str, email: str) -> bool:
    reply = llm.ask(f"{question} Answer yes or no.\n\nEmail:\n{email}", max_tokens=5)
    return reply.strip().lower().startswith("yes")


def classify(s: Triage) -> dict:
    label = llm.ask("Classify this support email as one of: billing, bug, account, feature. "
                    f"Reply with only the label.\n\n{s['email']}", max_tokens=8)
    return {"category": label.strip().lower()}


# The three checks write different keys, so LangGraph can merge them without a reducer.
def check_urgent(s: Triage) -> dict:
    return {"urgent": _yes("Does the sender want this handled today?", s["email"])}


def check_angry(s: Triage) -> dict:
    return {"angry": _yes("Is the sender angry or frustrated?", s["email"])}


def check_refund(s: Triage) -> dict:
    return {"refund": _yes("Is the sender asking for money back?", s["email"])}


def merge_flags(s: Triage) -> dict:  # pure, no LLM call
    return {"flags": [k for k in ("urgent", "angry", "refund") if s.get(k)]}


def mark_priority(s: Triage) -> dict:
    return {"priority": "high"}


def route_after_merge(s: Triage) -> str:
    """The `when` from module 5, as a conditional edge."""
    return "mark_priority" if s.get("urgent") else "ask_approval"


def ask_approval(s: Triage) -> dict:
    # interrupt() pauses the graph and saves state. On resume, this node runs again from the top
    # and interrupt() returns the resume value, so keep side effects after this line, never before.
    answer = interrupt(f"Approve drafting a reply? category={s['category']} flags={s['flags']}")
    return {"approved": str(answer)}


def draft_reply(s: Triage) -> dict:
    if s.get("approved", "").lower() not in ("yes", "true", "y"):
        return {"reply": ""}
    text = llm.ask(f"Draft a short, calm reply to this {s['category']} email. Flags: {s['flags']}.\n\n{s['email']}",
                   max_tokens=300)
    return {"reply": text}


def build(checkpointer):
    g = StateGraph(Triage)
    for fn in (classify, check_urgent, check_angry, check_refund, merge_flags,
               mark_priority, ask_approval, draft_reply):
        g.add_node(fn.__name__, fn)
    g.add_edge(START, "classify")
    for check in ("check_urgent", "check_angry", "check_refund"):
        g.add_edge("classify", check)                                  # fan out: these run in parallel
    g.add_edge(["check_urgent", "check_angry", "check_refund"], "merge_flags")  # join: waits for all three
    g.add_conditional_edges("merge_flags", route_after_merge, ["mark_priority", "ask_approval"])
    g.add_edge("mark_priority", "ask_approval")
    g.add_edge("ask_approval", "draft_reply")
    g.add_edge("draft_reply", END)
    return g.compile(checkpointer=checkpointer)


def open_saver(path: Path = DB) -> SqliteSaver:
    # check_same_thread=False because the parallel nodes run on worker threads.
    return SqliteSaver(sqlite3.connect(path, check_same_thread=False))


def main(argv) -> int:
    saver = open_saver()
    try:
        return run_cli(build(saver), argv)
    finally:
        saver.conn.close()


def run_cli(graph, argv) -> int:
    if argv[:1] == ["--resume"]:
        thread_id, answer = argv[1], argv[2]
        result = graph.invoke(Command(resume=answer), {"configurable": {"thread_id": thread_id}})
    else:
        thread_id = uuid.uuid4().hex[:8]
        email = " ".join(argv) or "I was charged twice. Fix it today."
        result = graph.invoke({"email": email}, {"configurable": {"thread_id": thread_id}})
    if "__interrupt__" in result:
        print(f"PAUSED: {result['__interrupt__'][0].value}")
        print(f"Resume with: python triage_graph.py --resume {thread_id} yes")
    else:
        print(f"category={result['category']} flags={result['flags']} priority={result.get('priority', 'normal')}")
        print(f"reply: {result['reply'] or '(not approved, nothing drafted)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
