"""Run 8 requests through the mega-agent and the team and count wrong-tool calls.

A call is wrong when the leaf tool is not in the set that request needs.

    python compare.py            # needs ANTHROPIC_API_KEY
    python compare.py --dry-run  # scripted fake, plumbing only
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402
import mega  # noqa: E402
import team  # noqa: E402

REQUESTS = [
    ("Where is order 1002?", {"get_order"}),
    ("What has Ana ordered so far?", {"list_orders"}),
    ("Is the blue kettle in stock?", {"search_products", "get_stock"}),
    ("Do you sell wool socks?", {"search_products"}),
    ("Has order 1003 been delivered?", {"get_order"}),
    ("How many desk lamps do we have left?", {"search_products", "get_stock"}),
    ("List Ben's orders.", {"list_orders"}),
    ("What is the status of order 1001 and is the kettle still available?",
     {"get_order", "search_products", "get_stock"}),
]


def wrong_calls(log, allowed):
    return [name for name in log if name not in allowed]


def run_setup(name, ask):
    total, wrong, errors = 0, 0, 0
    for request, allowed in REQUESTS:
        log = []
        try:
            ask(request, log)
        except RuntimeError as e:
            errors += 1
            print(f"  [{name}] {request!r}: {e}")
        total += len(log)
        wrong += len(wrong_calls(log, allowed))
    return name, len(REQUESTS), total, wrong, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        llm.FAKE = lambda body: llm.fake_text("dry run")
        print("DRY RUN: fake model, numbers are plumbing only.\n")
    rows = [run_setup("mega-agent", mega.ask), run_setup("team", team.ask)]
    print(f"\n{'setup':<12}{'requests':>9}{'leaf calls':>12}{'wrong-tool':>12}{'errors':>8}")
    print("-" * 53)
    for name, n, total, wrong, errors in rows:
        print(f"{name:<12}{n:>9}{total:>12}{wrong:>12}{errors:>8}")


if __name__ == "__main__":
    main()
