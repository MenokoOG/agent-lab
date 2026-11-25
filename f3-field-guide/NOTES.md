# f3 field guide notes

One task for every framework: "Which genre has the most books, and how many does it have?" with one tool, `count_by`. Measured on 2026-11-25 in WSL Ubuntu, Python 3.14 unless noted.

| framework | lines | install time | right answer? | offline test? | what it hid from me |
| --- | --- | --- | --- | --- | --- |
| hand-built (m2) | 99 (`loop.py` 40 + `tools.py` 59) | 0 s (stdlib) | not run live | yes, 8 tests | nothing; that's the point |
| LangGraph (F1) | 86 (`agent_graph.py`) | not timed alone (installed with Strands) | not run live | yes, 8 tests | the loop: `ToolNode` and `tools_condition` replace my for-loop; budget is `recursion_limit` |
| Strands (F2) | 78 (`book_agent.py`) | not timed alone | not run live | yes, 7 tests | the step budget; no limit unless I add one |
| Pydantic AI 2.74.0 | 24 | 31 s | not run live | yes, `FunctionModel` | probably the output validation retries inside `run_sync`; check on the live run |
| OpenAI Agents SDK 0.26.0 | 25 | 47 s | not run live | yes | the model call: Claude goes through LiteLLM, one more layer between me and the API |
| CrewAI 1.15.45 | 31 | 232 s failed on 3.14; 9 s with `uv` on Python 3.12 | not run live | yes (test skips the run) | the prompt: role, goal and backstory get written into a system prompt I never see |
| Google ADK 2.15.1 | 34 | 32 s | not run live | yes | sessions and the event stream; I dig the answer out of events |
| Claude Agent SDK 0.2.189 | 40 | 32 s | not run live | yes | the agent harness: built-in file and shell tools are on until `tools=[]` |

- "right answer?" needs one live call per framework. Run each `*_demo.py` with `ANTHROPIC_API_KEY` set and fill the column. The ADR waits on that column.
- CrewAI's install pulls a tiktoken build whose PyO3 tops out at Python 3.12. Fix: `uv venv -p 3.12 .venv-crew && uv pip install -p .venv-crew/bin/python "crewai[anthropic]"`.
