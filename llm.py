llm.py

"""Raw Messages API call shared by modules 2 to 10. Standard library only, no SDK.

Tests set llm.FAKE to a function (request body -> response dict), so nothing touches the network.
"""
import copy
import json
import os
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("LAB_MODEL", "claude-sonnet-5-5")
SMALL_MODEL = os.environ.get("LAB_SMALL_MODEL", "claude-haiku-5-5")
FAKE = None  # set to a callable in tests and dry runs


def chat(messages, *, system="", tools=None, model=None, max_tokens=1024):
    """One Messages API call. Returns the raw response dict."""
    body = {"model": model or MODEL, "max_tokens": max_tokens, "messages": messages}
    if system:
        body["system"] = system
    if tools:
        body["tools"] = tools
    if FAKE is not None:
        return FAKE(body)
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Set ANTHROPIC_API_KEY first.")
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST", headers={
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API {e.code}: {e.read().decode()}") from e


def text_of(resp):
    return "".join(b["text"] for b in resp["content"] if b["type"] == "text")


def ask(prompt, **kw):
    """One user message in, text out."""
    return text_of(chat([{"role": "user", "content": prompt}], **kw))


# Helpers for fakes. Responses have the same shape as the real API.
def fake_text(text, tokens=10):
    return {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn",
            "usage": {"input_tokens": tokens, "output_tokens": 5}}


def fake_tool_use(name, args, id="tu_1", tokens=10):
    return {"content": [{"type": "tool_use", "id": id, "name": name, "input": args}],
            "stop_reason": "tool_use", "usage": {"input_tokens": tokens, "output_tokens": 5}}


def scripted(*responses):
    """A fake that returns the given responses in order and records each request body."""
    it = iter(responses)
    bodies = []

    def fake(body):
        bodies.append(copy.deepcopy(body))  # the loop keeps appending to the same list
        return next(it)

    fake.bodies = bodies
    return fake