run.py

"""Run every prompt variant over tickets.csv and print one table.

    export ANTHROPIC_API_KEY=...
    python run.py                 # all variants on the main model
    python run.py --bonus         # also run the cheapest variant on the small model
    python run.py --dry-run       # fake model, checks the plumbing only
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import prompts

HERE = Path(__file__).parent
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("PROMPT_LAB_MODEL", "claude-sonnet-5-5")
SMALL_MODEL = os.environ.get("PROMPT_LAB_SMALL_MODEL", "claude-haiku-5-5")


def call_api(model: str, prompt: str, max_tokens: int = 16) -> tuple[str, int]:
    """One raw Messages API call. Returns (reply text, exact input tokens)."""
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API {e.code}: {e.read().decode()}") from e
    return data["content"][0]["text"], data["usage"]["input_tokens"]


def call_fake(model: str, prompt: str, max_tokens: int = 16) -> tuple[str, int]:
    """Dry-run stand-in. Picks a label from a hash. Numbers mean nothing."""
    time.sleep(0.01)
    h = int(hashlib.md5(prompt.encode()).hexdigest(), 16)
    return prompts.LABELS[h % len(prompts.LABELS)], len(prompt) // 4


def load_tickets() -> list[dict]:
    with open(HERE / "tickets.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ensure_seed_prompt(call, model: str) -> None:
    """Seed crystal: have the model write its own classification prompt once, then reuse it."""
    if prompts.SEED_PATH.exists():
        return
    text, _ = call(model, prompts.SEED_META_PROMPT, 600)
    text = text.strip()
    if "{ticket}" not in text:
        text += "\n\nTicket: {ticket}"
    prompts.SEED_PATH.write_text(text, encoding="utf-8")


def evaluate(name: str, build, model: str, rows: list[dict], call) -> dict:
    correct, tokens, latencies, misses = 0, [], [], []
    for row in rows:
        prompt = build(row["text"])
        start = time.perf_counter()
        reply, in_tokens = call(model, prompt)
        latencies.append(time.perf_counter() - start)
        tokens.append(in_tokens)
        pred = reply.strip().lower()  # exact match, no forgiving parse
        if pred == row["label"]:
            correct += 1
        else:
            misses.append({"text": row["text"], "want": row["label"], "got": reply.strip()})
    n = len(rows)
    return {
        "variant": name, "model": model, "accuracy": correct / n,
        "avg_input_tokens": sum(tokens) / n, "avg_latency_s": sum(latencies) / n,
        "misses": misses,
    }


def print_table(results: list[dict]) -> None:
    print(f"{'variant':<14}{'model':<20}{'accuracy':>9}{'avg in tok':>12}{'avg latency':>13}")
    print("-" * 68)
    for r in results:
        print(f"{r['variant']:<14}{r['model']:<20}{r['accuracy']:>9.0%}"
              f"{r['avg_input_tokens']:>12.1f}{r['avg_latency_s']:>12.2f}s")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="fake model, plumbing check only")
    ap.add_argument("--bonus", action="store_true", help="run cheapest variant on the small model")
    args = ap.parse_args()

    call = call_fake if args.dry_run else call_api
    if not args.dry_run and "ANTHROPIC_API_KEY" not in os.environ:
        print("Set ANTHROPIC_API_KEY first.", file=sys.stderr)
        return 1
    if args.dry_run:
        prompts.SEED_PATH = HERE / "seed_prompt.dryrun.txt"

    rows = load_tickets()
    ensure_seed_prompt(call, MODEL)

    results = [evaluate(name, fn, MODEL, rows, call) for name, fn in prompts.VARIANTS.items()]
    if args.bonus:
        cheapest = min(results, key=lambda r: r["avg_input_tokens"])
        small = evaluate(cheapest["variant"], prompts.VARIANTS[cheapest["variant"]],
                         SMALL_MODEL, rows, call)
        results.append(small)

    if args.dry_run:
        print("DRY RUN: fake model, numbers are plumbing only.\n")
    print_table(results)
    if args.bonus:
        print(f"\nBonus: {small['variant']} on {SMALL_MODEL} vs {MODEL}: "
              f"{small['accuracy'] - cheapest['accuracy']:+.0%} accuracy, "
              f"{small['avg_latency_s'] - cheapest['avg_latency_s']:+.2f}s latency.")

    out = HERE / ("results.dryrun.json" if args.dry_run else "results.json")
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nMisses and raw numbers: {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())