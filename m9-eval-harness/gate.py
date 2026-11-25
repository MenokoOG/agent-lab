"""CI gate: run the suite, compare with baseline.json, exit non-zero on regression.

    python gate.py            # exit 0 = ok, 1 = regression, 2 = no baseline yet
    python gate.py --dry-run  # same logic, fake agent
"""
import json
import sys
from pathlib import Path

import suite

BASELINE = Path(__file__).parent / "baseline.json"
TOLERANCE = 0.01


def passes(accuracy: float, baseline: float, tolerance: float = TOLERANCE) -> bool:
    return accuracy >= baseline - tolerance


def main(argv) -> int:
    if not BASELINE.exists():
        print("No baseline.json. Run `python suite.py --save-baseline` on a known-good version first.")
        return 2
    baseline = json.loads(BASELINE.read_text())["accuracy"]
    _, s = suite.run_all(dry_run="--dry-run" in argv)
    print(f"accuracy {s['accuracy']:.3f} (baseline {baseline:.3f})")
    if not passes(s["accuracy"], baseline):
        print("REGRESSION: accuracy dropped below the baseline.")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
