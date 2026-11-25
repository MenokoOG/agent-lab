"""Module 2's agent loop, rebuilt as a LangGraph graph: model node, tool node, and an edge that loops.

    python agent_graph.py "Which genre has the most books?"

Your run_agent had a for-loop, a stop check and a step budget. Here they become:
  for-loop      -> the edge from "tools" back to "model"
  stop check    -> tools_condition (go to "tools" if the model asked for one, else END)
  step budget   -> recursion_limit in the config
"""
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[1] / "m2-book-analyst"))
import llm  # noqa: E402
import tools as books  # noqa: E402  (module 2's pure functions)

SYSTEM = "You analyze a book corpus. Use the tools for counts and lists. Answer briefly."


# LangChain reads the name from the function and the description from the docstring.
@tool
def list_genres() -> str:
    """List every genre in the book corpus. Call this first when the user asks about categories."""
    return books.list_genres()


@tool
def books_by_genre(genre: str) -> str:
    """List the books (title and author) in one genre. Call when asked what is in a genre or who wrote a book."""
    return books.books_by_genre(genre)


@tool
def recs_by_person(person: str) -> str:
    """List the titles one person recommended. Call when asked what a named person recommended."""
    return books.recs_by_person(person)


@tool
def count_by(field: str) -> str:
    """Count books grouped by genre, recommender or author. Call for any how-many, most or least question."""
    return books.count_by(field)


TOOLS = [list_genres, books_by_genre, recs_by_person, count_by]


def default_model():
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(model=llm.MODEL, max_tokens=1024)


def build(model=None):
    bound = (model or default_model()).bind_tools(TOOLS)

    def call_model(state: MessagesState) -> dict:
        return {"messages": [bound.invoke([SystemMessage(SYSTEM)] + state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("model", call_model)
    # handle_tool_errors=True sends a tool's exception back to the model as an error message,
    # the same "surface, never swallow" rule as your loop. Without it, a tool error crashes the run.
    g.add_node("tools", ToolNode(TOOLS, handle_tool_errors=True))
    g.add_edge(START, "model")
    g.add_conditional_edges("model", tools_condition)  # "tools" or END
    g.add_edge("tools", "model")
    return g.compile()


def ask(question: str, model=None, max_steps: int = 8) -> dict:
    graph = build(model)
    out = graph.invoke({"messages": [HumanMessage(question)]}, {"recursion_limit": max_steps * 2})
    calls = [c["name"] for m in out["messages"] for c in getattr(m, "tool_calls", [])]
    return {"answer": out["messages"][-1].content, "tool_calls": calls, "messages": len(out["messages"])}


if __name__ == "__main__":
    r = ask(" ".join(sys.argv[1:]) or "Which genre has the most books?")
    print(r["answer"])
    print(f"[tools: {r['tool_calls']}]")
