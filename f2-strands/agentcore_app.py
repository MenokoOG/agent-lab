"""The book agent wrapped for Amazon Bedrock AgentCore Runtime. Optional, needs an AWS account to deploy.

    python agentcore_app.py      # serves locally on http://localhost:8080
    curl -s localhost:8080/invocations -H 'content-type: application/json' -d '{"prompt": "How many genres?"}'

Deploying is a separate step with the AgentCore starter toolkit. Follow the current Strands
"Deploy to Bedrock AgentCore" guide for the exact commands, because that tooling changes often.
"""
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from book_agent import build_agent

app = BedrockAgentCoreApp()
_agent = None


def get_agent():
    global _agent
    _agent = _agent or build_agent()
    return _agent


@app.entrypoint
def invoke(payload: dict) -> dict:
    prompt = payload.get("prompt")
    if not prompt:
        return {"error": "send JSON with a 'prompt' field"}
    return {"result": str(get_agent()(prompt))}


if __name__ == "__main__":
    app.run()
