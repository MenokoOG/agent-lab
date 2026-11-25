"""Structured context: keep state as a dict, compile it to a string before each call."""
from dataclasses import dataclass, field

PREFIXES = {"FACT:": "facts", "DECISION:": "decisions", "QUESTION:": "open_questions"}


@dataclass
class State:
    goal: str
    facts: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    open_questions: list = field(default_factory=list)


def update_from_text(state: State, text: str) -> State:
    """Pull FACT:, DECISION: and QUESTION: lines out of a message. Everything else is dropped."""
    for line in text.splitlines():
        line = line.strip()
        for prefix, attr in PREFIXES.items():
            if line.startswith(prefix):
                getattr(state, attr).append(line[len(prefix):].strip())
    return state


def compile_state(state: State) -> str:
    def block(title, items):
        return f"{title}:\n" + ("\n".join(f"- {i}" for i in items) if items else "- none")
    return "\n\n".join([f"Goal: {state.goal}", block("Decisions", state.decisions),
                        block("Facts", state.facts), block("Open questions", state.open_questions)])
