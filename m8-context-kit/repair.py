"""Feed errors back into context: run, read the error, fix, run again. Count repeated errors."""
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm  # noqa: E402


def run_py(code: str, timeout: int = 10) -> tuple:
    """Run code in a subprocess. A subprocess is NOT a sandbox. Module 10 fixes that."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
    try:
        p = subprocess.run([sys.executable, "-I", f.name], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 1, "", "TimeoutError: script ran too long"
    return p.returncode, p.stdout, p.stderr


def error_signature(stderr: str) -> str:
    lines = [l for l in stderr.strip().splitlines() if l.strip()]
    return lines[-1] if lines else "unknown error"


def prompt_hints(errors: Counter) -> list:
    """When the same error shows up twice, suggest a line for your prompt."""
    return [f"Add to the prompt: avoid this error ({sig}, seen {n} times)" for sig, n in errors.items() if n >= 2]


def solve_with_repair(task: str, max_tries: int = 3, ask=llm.ask) -> tuple:
    """Returns (stdout, hints). Raises when the retries run out."""
    errors = Counter()
    code = ask(f"Write a Python script for: {task}\nReturn only code, no markdown fences.")
    for _ in range(max_tries):
        rc, out, err = run_py(code)
        if rc == 0:
            return out, prompt_hints(errors)
        errors[error_signature(err)] += 1
        code = ask(f"Task: {task}\n\nCode:\n{code}\n\nError:\n{err}\n\nReturn the fixed code only, no markdown fences.")
    raise RuntimeError(f"still failing after {max_tries} tries. {prompt_hints(errors)}")
