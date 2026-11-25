# Use case: a support desk agent with a human in the loop

## The problem

A small online store gets support requests about orders, refunds, returns, shipping and accounts. Most answers sit in an order record or a policy page. A wrong answer about money costs more than a slow one, and an agent that reads customer text and can send replies is a prompt-injection target.

## Who uses it

- The customer writes a request.
- The support agent (a person) approves each reply before it goes out.
- The engineer who owns the desk reads the trace and the eval gate.

## What the agent does

1. Blocks a request that tries to give the agent new instructions.
2. Picks the orders or policy specialist.
3. Flags urgent requests and refund requests at the same time.
4. Looks up the order or searches the policy, through tools served over MCP.
5. Drafts a reply using the recent thread plus recalled older turns.
6. Waits for a person to approve. The wait can outlast a restart.
7. Checks the draft for leaked emails, keys or passwords, then sends it.
8. Remembers that a refund was approved, even after the thread is summarized.

## Limits on purpose

- The agent never sends on its own. That cuts the external-send leg of the lethal trifecta.
- Free-tier users get policy answers only. Order lookups need the pro tier or above.
- Unknown tiers get free-tier access.

## How I know it works

- 59 offline tests in `agentkit/tests/`, including the full flow, a rejected reply, a blocked injection, a leaky draft, tier limits, compaction and the MCP path.
- `examples/desk_eval.py` runs 8 cases and fails the build on regression. With the dry-run baseline, a broken router drops accuracy to 50% and the gate exits 1.
- Not yet measured: answer quality on a real model. That needs a live baseline run.

## Where it goes next

The same flow maps onto the planned Blue-Cottage-Mini supervisor-and-workers platform: router as supervisor, specialists as workers, the approval step as the human checkpoint. ADR 001 proposes LangGraph for the flow and Strands for the AWS deploy path.
