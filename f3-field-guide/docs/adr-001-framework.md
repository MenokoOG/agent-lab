# ADR 001: agent framework for agentkit

Status: proposed (needs the live "right answer?" column in NOTES.md before it's accepted)
Date: 2026-11-25

## Context
The capstone support desk needs to pause for a human approval and resume later, call tools over MCP, and eventually deploy on AWS. Typed output would help the eval suite.

## Options
- LangGraph: durable checkpoints and `interrupt()`. My F1 triage graph resumed from a new process (thread `f6733c60`). 136 lines against 200 for my mini-flow.
- Strands Agents: the same agent runs on the Anthropic API or Bedrock and serves for AgentCore. It listed my m4 MCP tools with no glue code. It hides the step budget.
- Pydantic AI: validated output and the best offline test story (`FunctionModel`). 24 lines, 31 s install.

## Decision
Proposed: LangGraph for the support desk flow, because approval-then-resume is the part I can't afford to get wrong, and its checkpoints already beat my JSON-file suspend. Strands stays the pick for the AWS deploy path. Lawrence decides.

## Consequences
- Easier: crash recovery mid-run, long waits on a human, graph tracing.
- Harder: another dependency tree, and the loop is less visible than my `run_agent`.
- Revisit if: the live runs show LangGraph getting the answer wrong more often than the others, or the deploy target becomes AgentCore only.
