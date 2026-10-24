"""A 30-message chat. Prints what actually reaches the model. No API calls."""
from dynamic import config_for
from memory import build_context, est_tokens, msg_text

FILLER = [
    "The weather turned cold and the roads were icy this morning.",
    "I am thinking about repainting the kitchen a lighter colour.",
    "Our team meeting moved to Thursday afternoon again.",
    "The new keyboard arrived and the keys feel much quieter.",
    "I should really renew my passport before the summer.",
]


def make_history(n: int = 30) -> list:
    history = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        history.append({"role": role, "content": f"{FILLER[i % len(FILLER)]} (message {i})"})
    history[2]["content"] = "My dog Biscuit is allergic to chicken, so we feed her fish."
    return history


if __name__ == "__main__":
    history = make_history()
    query = "What is my dog allergic to?"
    ctx = build_context(history, query, last_n=6, top_k=1, rng=1, limit=400)
    full = sum(est_tokens(msg_text(m)) for m in history)
    sent = sum(est_tokens(msg_text(m)) for m in ctx)
    print(f"full history: {len(history)} messages, ~{full} tokens")
    print(f"sent to model: {len(ctx)} messages, ~{sent} tokens\n")
    for m in ctx:
        print(f"{m['role']:>9}: {msg_text(m)}")
    cfg = config_for("pro", "English")
    print(f"\ntier pro -> model={cfg.model}, tools={cfg.tool_names}, top_k={cfg.top_k}")