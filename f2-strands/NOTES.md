# f2 strands notes

- 7 tests pass (strands-agents 1.66.0, mcp 2.3.0).
- Strands listed the tools from my m4 server over stdio: `['list_genres', 'books_by_genre', 'recs_by_person', 'count_by']`.
- Lines: `book_agent.py` is 78. My `loop.py` + `tools.py` is 99.
- What Strands hides that I'd want in production: the step budget. My loop raises after `max_steps`. Strands runs its event loop until the model stops, so I'd add a hook or limit before I let it run unattended.
- Not run: a live question, Bedrock (`STRANDS_PROVIDER=bedrock`) and the AgentCore app. They spend tokens or need AWS setup.
