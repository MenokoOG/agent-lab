"""Run model-written code in a container: no network, capped memory, cpu and processes, read-only.

    python sandbox.py --probe      # proves the container cannot reach the network
Needs Docker. If Docker isn't installed, use a hosted sandbox such as E2B or Daytona instead.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

IMAGE = "python:3.12-slim"

NETWORK_PROBE = """
import socket
try:
    socket.create_connection(("1.1.1.1", 53), timeout=3)
    print("NETWORK REACHABLE")
except OSError:
    print("network blocked")
"""


def docker_cmd(code_dir: str, script: str = "main.py") -> list:
    return ["docker", "run", "--rm",
            "--network", "none",        # no outbound path, so nothing to exfiltrate through
            "--memory", "256m", "--cpus", "0.5", "--pids-limit", "64",
            "--read-only", "--tmpfs", "/tmp:size=16m",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "-v", f"{code_dir}:/work:ro", "-w", "/work",
            IMAGE, "python", "-I", script]


def docker_available() -> bool:
    """True only when the CLI exists and the daemon answers."""
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=10).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def run_sandboxed(code: str, timeout: int = 20) -> tuple:
    """Returns (returncode, stdout, stderr)."""
    if not docker_available():
        raise RuntimeError("Docker is not installed or its daemon is not running. Start it, or use a hosted sandbox.")
    with tempfile.TemporaryDirectory() as d:
        # mkdtemp makes the folder 0700. With --cap-drop ALL, root in the container loses
        # CAP_DAC_OVERRIDE, so it can't read a folder owned by the host user. Open it read-only.
        Path(d).chmod(0o755)
        script = Path(d, "main.py")
        script.write_text(code)
        script.chmod(0o644)
        p = subprocess.run(docker_cmd(d), capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


if __name__ == "__main__":
    if "--probe" in sys.argv:
        rc, out, err = run_sandboxed(NETWORK_PROBE)
        print(out.strip() or err.strip())
        sys.exit(0 if "blocked" in out else 1)
    print(__doc__)
