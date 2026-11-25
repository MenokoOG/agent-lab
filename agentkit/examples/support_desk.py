"""Support desk: one agent that uses every agentkit module.

    python examples/support_desk.py --user ana --tier pro "Order 1001 was charged twice, refund me today"
    python examples/support_desk.py --resume RUN_ID yes
    python examples/support_desk.py --local ...     # in-process tools instead of the MCP server
    python examples/support_desk.py --dry-run ...   # scripted fake model, no API key, no spend

Flow: input guard -> route -> parallel checks -> priority -> specialist answer -> human approval
(suspends, survives a restart) -> output guard -> send to the outbox -> remember and compact.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentkit import llm  # noqa: E402
from agentkit.context import State, compact  # noqa: E402
from agentkit.dynamic import config_for, pick_tools  # noqa: E402
from agentkit.flow import Flow, Run, Suspend  # noqa: E402
from agentkit.guards import DEFAULT_MESSAGE, input_guard, output_guard  # noqa: E402
from agentkit.memory import build_context  # noqa: E402
from agentkit.team import Specialist, route  # noqa: E402
from agentkit.tools import McpToolset  # noqa: E402
from examples import desk_data  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "var"
SERVER = HERE / "desk_server.py"
APPROVED = ("yes", "y", "true", "approve", "approved")


_MCP: Optional[McpToolset] = None


def tool_source(use_mcp: bool):
    """Same interface either way: list_tools() and handlers(). One MCP toolset per process."""
    global _MCP
    if not use_mcp:
        return desk_data.registry
    if _MCP is None:
        _MCP = McpToolset(sys.executable, [str(SERVER)])
    return _MCP


def specialists_for(tier: str, use_mcp: bool) -> List[Specialist]:
    cfg = config_for(tier)
    source = tool_source(use_mcp)
    tools = pick_tools(cfg, source.list_tools())
    handlers = {n: h for n, h in source.handlers().items() if n in cfg.allowed_tools}

    def subset(names):
        chosen = [t for t in tools if t["name"] in names]
        return chosen, {t["name"]: handlers[t["name"]] for t in chosen}

    o_tools, o_handlers = subset({"lookup_order", "escalate"})
    p_tools, p_handlers = subset({"search_policy", "escalate"})
    return [
        Specialist("orders", "Order status, charges on an order, anything with an order number.",
                   f"{cfg.system} You handle order questions. Use your tools, quote the order status.",
                   o_tools, o_handlers),
        Specialist("policy", "Refund, return, shipping and account rules.",
                   f"{cfg.system} You answer from store policy only. Use search_policy.", p_tools, p_handlers),
    ]


def _yes(question: str, text: str) -> bool:
    reply = llm.ask(f"{question} Answer yes or no.\n\nMessage:\n{text}", model=llm.SMALL_MODEL, max_tokens=5)
    return reply.strip().lower().startswith("yes")


class Thread:
    """Per-user memory on disk: message history plus a decision list that survives compaction."""

    def __init__(self, user: str, root: Path = DATA) -> None:
        self.path = root / "threads" / f"{user}.json"
        raw = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.history: List[dict] = raw.get("history", [])
        self.state = State(goal=f"support for {user}", decisions=raw.get("decisions", []))

    def remember(self, request: str, reply: str, decision: Optional[str], threshold: int) -> None:
        if decision:
            self.state.add("decisions", decision)
        self.history += [{"role": "user", "content": request}, {"role": "assistant", "content": reply}]
        self.history = compact(self.history, threshold, keep_last=4, must_keep=self.state.decisions)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"history": self.history, "decisions": self.state.decisions}, indent=2))


def build_flow(use_mcp: bool = True, root: Path = DATA) -> Flow:
    def triage(s):
        names = {sp.name: sp for sp in specialists_for(s["tier"], use_mcp)}
        return {"specialist": route(s["request"], list(names.values()), default="policy")}

    def check_urgent(s):
        return {"urgent": _yes("Does the customer want this handled today?", s["request"])}

    def check_refund(s):
        return {"refund": _yes("Is the customer asking for money back?", s["request"])}

    def mark_priority(s):
        return {"priority": "high"}

    def answer(s):
        cfg = config_for(s["tier"])
        thread = Thread(s["user"], root)
        team = {sp.name: sp for sp in specialists_for(s["tier"], use_mcp)}
        goal = build_context(thread.history, s["request"], limit=cfg.memory_limit)
        result = team[s["specialist"]].run(goal, model=cfg.model)
        return {"draft": result.answer, "tools_used": result.tool_calls}

    def approval(s):
        return Suspend(f"Send this reply? specialist={s['specialist']} refund={s['refund']} "
                       f"priority={s.get('priority', 'normal')}\n---\n{s['draft']}")

    def send(s):
        approved = str(s.get("approved", "")).lower() in APPROVED
        if not approved:
            return {"sent": False, "reply": None, "held": "not approved"}
        check = output_guard(s["draft"])
        reply = DEFAULT_MESSAGE if check.blocked else s["draft"]
        outbox = root / "outbox.jsonl"
        outbox.parent.mkdir(parents=True, exist_ok=True)
        with outbox.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"user": s["user"], "reply": reply}) + "\n")
        decision = "refund approved by a human agent" if s["refund"] else None
        Thread(s["user"], root).remember(s["request"], reply, decision, config_for(s["tier"]).memory_limit)
        return {"sent": True, "reply": reply, "held": check.reason if check.blocked else ""}

    return (Flow("support_desk", store=root / "runs")
            .then(triage)
            .parallel(check_urgent, check_refund)
            .when(lambda s: s["urgent"], mark_priority)
            .then(answer)
            .then(approval)
            .then(send))


def handle(request: str, user: str, tier: str, use_mcp: bool = True, root: Path = DATA) -> Run:
    """The input guard runs before the flow, so a blocked request never reaches a model."""
    from agentkit.flow import Trace
    if input_guard(request).blocked:
        return Run("blocked", "done", {"reply": DEFAULT_MESSAGE, "sent": False, "held": "input guard"}, Trace())
    return build_flow(use_mcp, root).run({"request": request, "user": user, "tier": tier})


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("request", nargs="*")
    ap.add_argument("--user", default="ana")
    ap.add_argument("--tier", default="pro")
    ap.add_argument("--resume", nargs=2, metavar=("RUN_ID", "ANSWER"))
    ap.add_argument("--local", action="store_true", help="in-process tools instead of MCP")
    ap.add_argument("--dry-run", action="store_true", help="scripted fake model, no spend")
    args = ap.parse_args(argv)
    if args.dry_run:
        from examples.fake_model import desk_fake
        llm.FAKE = desk_fake
    use_mcp = not args.local
    if args.resume:
        run = build_flow(use_mcp).resume(args.resume[0], {"approved": args.resume[1]})
    else:
        run = handle(" ".join(args.request) or "Order 1001 was charged twice, refund me today", args.user,
                     args.tier, use_mcp)
    print("\n".join(run.trace.tree()))
    if run.status == "suspended":
        flag = " --dry-run" if args.dry_run else ""
        print(f"\nSUSPENDED: {run.reason}\nResume with: python examples/support_desk.py --resume {run.run_id} yes"
              f"{flag}{' --local' if args.local else ''}")
    else:
        print(f"\nsent={run.state.get('sent')} reply: {run.state.get('reply')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
