"""Step 1: your own loop reads the tools from the registry instead of a hard-coded list."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))
import registry  # noqa: E402
from loop import run_agent  # noqa: E402

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Which genre has the most books?"
    r = run_agent(question, registry.list_tools(), registry.handlers(),
                  system="You analyze a book corpus. Use the tools.")
    print(r.answer)
    print(f"[{r.steps} steps, tools: {r.tool_calls}]")
