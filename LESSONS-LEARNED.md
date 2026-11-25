# Lessons learned

What the Agent Builder Course taught me, module by module, plus the bugs that cost time. Modules 1 to 3 I built by hand in October. Modules 4 to 10, the framework lessons and the capstone were built on 2026-11-25 with Claude Code from the course reference builds, then tested offline. Live model runs are still open and listed at the end.

## By module

- **m1 prompting.** Few-shot plus XML is the shape I'd start with. Measure every prompt change; small wording moves the score.
- **m2 first agent.** An agent is a bounded loop. Send tool errors back to the model as `is_error` results. Swallowing them hides the failure, and crashing ends a run the model could have fixed.
- **m3 memory.** A sliding window forgets facts from 20 turns back. Recall plus a window keeps them. Filter old tool results so the agent calls the tool again instead of trusting stale data.
- **m3 dynamic agents.** Pick the model, tools and limits from user context. An unknown tier should get the least access.
- **m4 MCP.** The registry is what MCP standardizes. Once the tools sat behind `server.py`, Strands used them with zero glue code. Clients and servers on different `mcp` majors drift: 2.x renamed `FastMCP` and `inputSchema`.
- **m5 workflows.** One LLM call per step makes a flow easy to debug. Suspend has to write state to disk, or a restart loses the run. I proved resume across two processes for both my engine and LangGraph.
- **m6 RAG.** Climb the ladder: full context, then tools, then RAG. Count and "which has the most" questions break retrieval, because no single chunk holds the answer. A tool over the CSV does.
- **m7 multi-agent.** Split an agent when it has too many tools to pick from. A one-call router is cheap; a supervisor that calls specialists as tools is flexible and costs more.
- **m8 context.** In the 60-turn dry run, naive append averaged 11,651 input tokens per call. Compaction cut that to 1,212, and structured state to 90. Summaries drop detail, so decisions go in a must-keep list that's copied verbatim.
- **m9 evals.** Binary PASS or FAIL beats a 1 to 10 score. Tag each failure with a mode (wrong route, wrong answer, budget) so I know which fix pays most. A gate needs a baseline from a known-good live run, or it has nothing to compare against.
- **m10 security.** Rate every agent on the lethal trifecta: private data, untrusted input, external send. Cut a leg. In the capstone, a human approval before send cuts the send leg. Regex guards caught 8 of 10 injections; the 2 misses were indirect asks with no "ignore" phrase.
- **F1 to F3 frameworks.** Each framework hides something. LangGraph hides the loop, Strands hides the step budget, CrewAI hides the prompt. Building by hand first is how I know what to look for.

## Bugs that cost time

- `llm.py` had a stray first line, `llm.py`, from a paste. Every import failed with `NameError: name 'llm' is not defined`. Check the first line of a pasted file.
- The Docker sandbox couldn't read its own script. `tempfile.TemporaryDirectory` makes a 0700 folder, and `--cap-drop ALL` removes root's `CAP_DAC_OVERRIDE`, so root in the container can't read a folder owned by uid 1000. Set 0755 and 0644 before mounting.
- CrewAI wouldn't install on Python 3.14. Its tiktoken pin builds PyO3 0.20, which supports up to 3.12. `uv venv -p 3.12` fixed it in 9 seconds.
- `mcp` 2.x returns `Tool.input_schema`; 1.x returned `inputSchema`. agentkit reads both.

## Open in my own m1 code

- `single_shot()` in `m1-prompt-lab/prompts.py` includes all 4 examples, so it's few-shot. It should use 1.
- `few_shot()` defaults to `n=2`. The spec says 4.
- The table in `m1-prompt-lab/NOTES.md` shows 0.01 s latency on every row, which looks like dry-run output. Rerun `python run.py --bonus` with a key after the two fixes.

## Still needs a live run (spends tokens)

- m1 `run.py --bonus`, m6 `ladder.py`, m7 `compare.py`, m8 `experiment.py`.
- m9 `suite.py --save-baseline`, then `gate.py`.
- m10 `guards.py --model`.
- F1 `agent_graph.py`, F2 `book_agent.py`, and each F3 `*_demo.py` to fill the "right answer?" column.
- agentkit `examples/desk_eval.py --save-baseline`, then the gate without `--dry-run`.
