# agentkit

The ten Agent Builder Course projects merged into one small framework, plus a support desk that uses all of it. Standard library only, except `mcp` for the MCP server and client.

## Layout

| file | module | what it does |
| --- | --- | --- |
| `agentkit/llm.py` | setup | raw Messages API client; `llm.FAKE` swaps in a fake model |
| `agentkit/prompts.py` | m1 | zero-shot, few-shot, XML structure, strict label parsing |
| `agentkit/loop.py` | m2 | `run_agent`: bounded loop, tool errors sent back to the model |
| `agentkit/tools.py` | m2, m4 | `Registry`, `serve_mcp`, `McpToolset` (MCP client over stdio) |
| `agentkit/memory.py` | m3 | window, TF-IDF recall, token limiter, tool-call filter |
| `agentkit/dynamic.py` | m3 | `config_for(tier)`: model, prompt, tools and limits per user tier |
| `agentkit/flow.py` | m5 | then, parallel, when, suspend, resume, span tree |
| `agentkit/rag.py` | m6 | chunk, TF-IDF index, top k, model rerank |
| `agentkit/team.py` | m7 | `Specialist`, `agent_as_tool`, one-call `route`, `supervisor` |
| `agentkit/context.py` | m8 | compaction with a must-keep list, structured state, repair loop |
| `agentkit/evals.py` | m9 | binary judge, suite with failure modes, baseline gate |
| `agentkit/guards.py` | m10 | input and output guards, trifecta audit, Docker sandbox |
| `examples/support_desk.py` | all | the end-to-end task |
| `examples/desk_eval.py` | m9 | 8-case eval suite and CI gate for the desk |

## Run it

From `agentkit/`, with the repo venv active. The `--dry-run` flag uses a scripted fake model and spends nothing.

```bash
python -m unittest discover -s tests -t .
```

```bash
python examples/support_desk.py --dry-run "Order 1001 was charged twice, refund me today"
```

```bash
python examples/support_desk.py --dry-run --resume RUN_ID yes
```

```bash
python examples/desk_eval.py --dry-run
```

Drop `--dry-run` for a real run. That needs `ANTHROPIC_API_KEY` and spends tokens. Save a real baseline once with `python examples/desk_eval.py --save-baseline`, then the plain command is the gate.

## The support desk flow

1. Input guard. A blocked request never reaches a model (m10).
2. `config_for(tier)` picks the model, tools and memory limit (m3).
3. `route` picks the orders or policy specialist in one small-model call (m7).
4. Two checks run in parallel: urgent and refund. Urgent sets high priority (m5).
5. The specialist answers with tools served by `examples/desk_server.py` over MCP (m4). Policy questions go through the RAG index (m6). Memory feeds it the recent window plus recalled older turns (m3).
6. The flow suspends for human approval. Nothing is sent while it waits, and the run survives a restart (m5).
7. On approval, the output guard checks the draft, then it goes to `var/outbox.jsonl` (m10).
8. The thread is saved and compacted. "refund approved by a human agent" stays in the must-keep list (m8).
9. `desk_eval.py` fails the build when accuracy drops below the baseline (m9).

## Decisions

- One package with no `sys.path` tricks. The course modules import each other by path; a framework can't.
- MCP is the default tool path, and `--local` uses the same registry in-process. Tests cover both.
- `McpToolset` opens a session per tool call. That's a process start each time. It keeps the class thread-free, and it's too slow for a service.
- The input guard runs before the flow, so an injection never gets a run id or a saved state.
- Unknown tiers get the free tier, never the most access.
- The trifecta audit rates the desk 2/3 legs. It reads private orders and untrusted customer text. Its only send runs after a human approves, so the agent can't send on its own.

## What I cut

- Streaming, retries on 429 and 529, and cost tracking in `llm.py`.
- A real embedding model. TF-IDF is enough for 4 policy files.
- The model-based input guard in the desk. It exists in `guards.py` and is off by default because it costs a call per request.
- Multi-user locking on `var/`. Two workers resuming the same run would race.

## What I'd do differently

- Hold one MCP session open for the life of the process.
- Put the flow state in SQLite. LangGraph's checkpointer (F1) saves after every node, and mine saves only at a suspend.
- Write the eval cases first. The 8 cases came after the desk. On the fake model they score 100%, which proves the wiring and says nothing about the model.

## Framework rebuild

F1 rebuilt the m5 triage flow in LangGraph: 136 lines against 200 for `flow.py` plus `triage.py`. It resumed a paused run from a new process with the fake model. What it saved: the checkpoint store, the resume bookkeeping and the parallel join. What it cost: a second dependency tree and a loop I can't read in one screen. ADR 001 in `f3-field-guide/docs/` holds the proposed pick.
