"""How often does the judge agree with you? Fill hand_grades.csv (hand_pass = yes or no) after a real run.

    python judge_check.py
"""
import csv
import json
from pathlib import Path

from judge import agreement

HERE = Path(__file__).parent

if __name__ == "__main__":
    results = {r["id"]: r for r in json.loads((HERE / "results.json").read_text())}
    with open(HERE / "hand_grades.csv", newline="", encoding="utf-8") as f:
        hand = {r["id"]: r["hand_pass"].strip().lower() == "yes" for r in csv.DictReader(f) if r["hand_pass"].strip()}
    n, agree, bad = agreement({i: r["passed"] for i, r in results.items()}, hand)
    print(f"graded by hand: {n}   agreement: {agree}/{n}" if n else "Fill in hand_grades.csv first.")
    for i in bad:
        r = results[i]
        print(f"  DISAGREE {i}: judge={'PASS' if r['passed'] else 'FAIL'} you={'PASS' if hand[i] else 'FAIL'}"
              f"\n    Q: {r['question']}\n    A: {r['answer']}")
