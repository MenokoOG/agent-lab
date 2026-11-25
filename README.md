# agent-lab

My build of the Agent Builder Course, a 10-module course I wrote for myself from Sam Bhagwat's *Principles of Building AI Agents* and *Patterns for Building AI Agents*. Each module is a small Python project. The capstone, `agentkit/`, merges all ten into one framework with a support desk example.

## Layout

| folder | module | project |
| --- | --- | --- |
| `m1-prompt-lab/` | 1 | prompt variants scored on 20 tickets |
| `m2-book-analyst/` | 2 | the agent loop and tools |
| `m3-memory-kit/` | 3 | memory processors and dynamic config |
| `m4-tool-server/` | 4 | tool registry and MCP server |
| `m5-mini-flow/` | 5 | workflow engine with suspend and resume |
| `m6-rag-ladder/` | 6 | full context, tools, then RAG by hand |
| `m7-agent-org/` | 7 | router and specialists vs one mega-agent |
| `m8-context-kit/` | 8 | compaction, structured state, repair loop |
| `m9-eval-harness/` | 9 | golden set, judge, CI gate |
| `m10-trifecta-audit/` | 10 | guards, trifecta audit, Docker sandbox |
| `f1-langgraph/` | F1 | m2 and m5 rebuilt in LangGraph |
| `f2-strands/` | F2 | m2, m4 and m7 rebuilt in Strands Agents |
| `f3-field-guide/` | F3 | one task in five frameworks, ADR 001 |
| `agentkit/` | capstone | the merged framework |

`llm.py` is the shared raw Messages API client. Every test swaps in a fake model, so the suite needs no key and spends nothing.

## Setup

WSL Ubuntu, Python 3.12 or newer.

```bash
python3 -m venv .venv && source .venv/bin/activate
```

```bash
pip install -r f1-langgraph/requirements.txt -r f2-strands/requirements.txt
```

```bash
./test_all.sh
```

F3 frameworks each get their own venv. The commands are in `f3-field-guide/NOTES.md`.

## Docs

- [LESSONS-LEARNED.md](LESSONS-LEARNED.md): what each module taught, and the bugs I hit.
- [USE-CASE.md](USE-CASE.md): the support desk use case the capstone solves.
- [agentkit/README.md](agentkit/README.md): the framework, its decisions and what I cut.
- [CHANGELOG.md](CHANGELOG.md)
