"""Rate each agent against the lethal trifecta. Edit agents.json to match what you actually built.

    python audit.py
"""
import json
from dataclasses import dataclass, replace
from pathlib import Path

LEGS = ("reads_private_data", "reads_untrusted_content", "can_send_externally")


@dataclass(frozen=True)
class AgentSpec:
    name: str
    reads_private_data: bool
    reads_untrusted_content: bool
    can_send_externally: bool


def trifecta_risk(a: AgentSpec) -> str:
    legs = [getattr(a, leg) for leg in LEGS]
    if all(legs):
        return f"{a.name}: HIGH. Remove one leg (usually external send) or add input processing."
    return f"{a.name}: ok ({sum(legs)}/3 legs)"


def without_leg(a: AgentSpec, leg: str) -> AgentSpec:
    """Cut a leg and re-run the rating. This is the fix, expressed as data."""
    if leg not in LEGS:
        raise ValueError(f"leg must be one of {LEGS}")
    return replace(a, **{leg: False})


def load_specs(path=Path(__file__).parent / "agents.json") -> list:
    return [AgentSpec(**row) for row in json.loads(Path(path).read_text())]


if __name__ == "__main__":
    for spec in load_specs():
        line = trifecta_risk(spec)
        print(line)
        if "HIGH" in line:
            print("   after cutting can_send_externally ->", trifecta_risk(without_leg(spec, "can_send_externally")))
