"""Pick the model in one place. Default is the Anthropic API (uses ANTHROPIC_API_KEY, no AWS needed).

    STRANDS_PROVIDER=bedrock python book_agent.py ...   # uses your AWS credentials and Bedrock instead
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402  (for the shared MODEL name)


def make_model():
    provider = os.environ.get("STRANDS_PROVIDER", "anthropic")
    if provider == "anthropic":
        from strands.models.anthropic import AnthropicModel
        return AnthropicModel(model_id=llm.MODEL, max_tokens=1024)
    if provider == "bedrock":
        from strands.models.bedrock import BedrockModel
        # Bedrock model ids differ from Anthropic API ids. Check the Bedrock console for the ones you can use.
        return BedrockModel(model_id=os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6"),
                            region_name=os.environ.get("AWS_REGION", "us-west-2"))
    raise ValueError("STRANDS_PROVIDER must be anthropic or bedrock")
