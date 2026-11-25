"""m1: prompt variants and structure helpers.

Module 1 showed few-shot plus XML structure is the most controllable shape. These helpers build it
so every agent in the kit writes prompts the same way.
"""
from typing import Iterable, Sequence, Tuple

Example = Tuple[str, str]


def xml_block(tag: str, body: str) -> str:
    return f"<{tag}>{body}</{tag}>"


def zero_shot(task: str, rule: str, item: str) -> str:
    return f"{task}\n{rule}\n\nInput: {item}\nOutput:"


def few_shot(task: str, rule: str, examples: Sequence[Example], item: str) -> str:
    if not examples:
        raise ValueError("few_shot needs at least one example; use zero_shot instead")
    shots = "\n".join(f"Input: {i}\nOutput: {o}" for i, o in examples)
    return f"{task}\n{rule}\n\n{shots}\n\nInput: {item}\nOutput:"


def structured(task: str, constraints: Iterable[str], examples: Sequence[Example], item: str,
               item_tag: str = "input") -> str:
    """Task, constraints, examples and input, each in its own tag."""
    parts = [xml_block("task", task),
             xml_block("constraints", " ".join(constraints))]
    if examples:
        shots = "\n".join(f"<example><input>{i}</input><output>{o}</output></example>" for i, o in examples)
        parts.append(xml_block("examples", "\n" + shots + "\n"))
    parts.append(xml_block(item_tag, item))
    return "\n".join(parts)


def pick_label(reply: str, labels: Sequence[str], default: str) -> str:
    """Strict parse: the stripped, lowercased reply must be one of the labels."""
    cleaned = reply.strip().lower().rstrip(".")
    return cleaned if cleaned in labels else default
