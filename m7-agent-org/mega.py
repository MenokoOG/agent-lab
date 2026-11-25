"""One agent with every tool. The baseline the team has to beat."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))  # append, so local names win
from loop import run_agent  # noqa: E402
from shop import LEAF_HANDLERS, LEAF_TOOLS, logged  # noqa: E402


def ask(request: str, log: list) -> str:
    return run_agent(request, LEAF_TOOLS, logged(LEAF_HANDLERS, log),
                     system="You answer shop requests using your tools. Be brief.").answer
