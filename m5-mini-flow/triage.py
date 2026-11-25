"""The support workflow: classify, check three things in parallel, merge, wait for a human, draft.

    python triage.py "Hi, I was charged twice and I'm furious. Fix it today."
    python triage.py --resume RUN_ID yes
Every step makes at most one LLM call.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402
from flow import Flow, Suspend  # noqa: E402


def _yes(question, email):
    return llm.ask(f"{question} Answer yes or no.\n\nEmail:\n{email}", max_tokens=5).strip().lower().startswith("yes")


def classify(s):
    label = llm.ask("Classify this support email as one of: billing, bug, account, feature. "
                    f"Reply with only the label.\n\n{s['email']}", max_tokens=8)
    return {"category": label.strip().lower()}


def check_urgent(s):
    return {"urgent": _yes("Does the sender want this handled today?", s["email"])}


def check_angry(s):
    return {"angry": _yes("Is the sender angry or frustrated?", s["email"])}


def check_refund(s):
    return {"refund": _yes("Is the sender asking for money back?", s["email"])}


def merge_flags(s):  # pure, no LLM call
    flags = [k for k in ("urgent", "angry", "refund") if s.get(k)]
    return {"flags": flags}


def mark_priority(s):  # runs only when the condition below is true
    return {"priority": "high"}


def ask_approval(s):
    return Suspend(f"Approve drafting a reply? category={s['category']} flags={s['flags']}")


def draft_reply(s):
    if str(s.get("approved", "")).lower() not in ("yes", "true", "y"):
        return {"reply": None}
    reply = llm.ask(f"Draft a short, calm reply to this {s['category']} email. Flags: {s['flags']}.\n\n{s['email']}",
                    max_tokens=300)
    return {"reply": reply}


def build_flow():
    return (Flow("triage")
            .then(classify)
            .parallel(check_urgent, check_angry, check_refund)
            .then(merge_flags)
            .when(lambda s: s["urgent"], mark_priority)
            .then(ask_approval)
            .then(draft_reply))


if __name__ == "__main__":
    flow = build_flow()
    if len(sys.argv) > 1 and sys.argv[1] == "--resume":
        run = flow.resume(sys.argv[2], {"approved": sys.argv[3]})
    else:
        run = flow.run({"email": " ".join(sys.argv[1:]) or "I was charged twice. Fix it today."})
    run.trace.print_tree()
    if run.status == "suspended":
        print(f"\nSUSPENDED: {run.reason}\nResume with: python triage.py --resume {run.run_id} yes")
    else:
        print(f"\nreply: {run.state['reply']}")
