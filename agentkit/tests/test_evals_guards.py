"""m9 evals and gate, m10 guards, trifecta audit and sandbox."""
import tempfile
import unittest
from pathlib import Path

from agentkit import guards
from agentkit.evals import Case, gate, run_suite, save_baseline, summarize

CASES = [Case("1", "q1", "a1", "t1", "x"), Case("2", "q2", "a2", "t2", "y")]


def exact(q, ref, ans):
    return ref == ans


class EvalTests(unittest.TestCase):
    def test_failure_modes(self):
        def agent(q):
            if q == "q1":
                return "a1", ["wrong_tool"]
            raise RuntimeError("step budget exhausted")
        s = summarize(run_suite(agent, CASES, exact))
        self.assertEqual(s["failure_modes"], {"wrong_route": 1, "budget_or_error": 1})

    def test_gate_passes_good_and_fails_broken(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "baseline.json")
            self.assertEqual(gate({"accuracy": 1.0}, path)[0], 2)  # no baseline yet
            good = summarize(run_suite(lambda q: ("a" + q[1], ["t" + q[1]]), CASES, exact))
            save_baseline(good, path)
            self.assertEqual(gate(good, path)[0], 0)
            broken = summarize(run_suite(lambda q: ("nope", ["t" + q[1]]), CASES, exact))
            self.assertEqual(gate(broken, path)[0], 1)


class GuardTests(unittest.TestCase):
    def test_blocks_at_least_8_of_10_injections(self):
        cases = [ln for ln in (Path(__file__).parent / "injection_cases.txt").read_text().splitlines() if ln.strip()]
        blocked = sum(guards.input_guard(c).blocked for c in cases)
        self.assertGreaterEqual(blocked, 8, f"blocked only {blocked}/10")

    def test_benign_text_passes(self):
        self.assertFalse(guards.input_guard("Where is my order 1001?").blocked)

    def test_output_guard_and_retry(self):
        self.assertTrue(guards.output_guard("mail me at a@b.co").blocked)
        outs = iter(["key sk-abcdefghijklmnopqrstu", "clean answer"])
        self.assertEqual(guards.guarded_call(lambda t: next(outs), "hello"), "clean answer")
        self.assertEqual(guards.guarded_call(lambda t: "a@b.co", "hello", retries=1), guards.DEFAULT_MESSAGE)

    def test_trifecta(self):
        spec = guards.AgentSpec("desk", True, True, True)
        self.assertIn("HIGH", guards.trifecta_risk(spec))
        self.assertIn("ok", guards.trifecta_risk(guards.without_leg(spec, "can_send_externally")))

    def test_docker_command_isolation_flags(self):
        joined = " ".join(guards.docker_cmd("/tmp/x"))
        for flag in ("--network none", "--read-only", "--cap-drop ALL", ":/work:ro"):
            self.assertIn(flag, joined)

    @unittest.skipUnless(guards.docker_available(), "Docker is not running here")
    def test_sandbox_has_no_network(self):
        probe = ("import socket\ntry:\n    socket.create_connection(('1.1.1.1', 53), timeout=3)\n"
                 "    print('NETWORK REACHABLE')\nexcept OSError:\n    print('network blocked')\n")
        rc, out, err = guards.run_sandboxed(probe)
        self.assertIn("network blocked", out, err)


if __name__ == "__main__":
    unittest.main()
