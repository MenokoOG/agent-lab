"""m5 workflow engine."""
import tempfile
import unittest
from pathlib import Path

from agentkit.flow import Flow, Suspend


def add(key, value):
    def step(s):
        return {key: value}
    step.__name__ = f"set_{key}"
    return step


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name)

    def test_chain_parallel_and_condition(self):
        f = (Flow("t", self.store).then(add("a", 1)).parallel(add("b", 2), add("c", 3))
             .when(lambda s: s["b"] == 2, add("d", 4)).when(lambda s: False, add("e", 5)))
        run = f.run({})
        self.assertEqual(run.state, {"a": 1, "b": 2, "c": 3, "d": 4})
        self.assertEqual(run.status, "done")

    def test_suspend_then_resume_from_a_new_flow_object(self):
        def build():
            return Flow("t", self.store).then(add("a", 1)).then(lambda s: Suspend("ok?")).then(
                lambda s: {"result": f"approved={s['approved']}"})
        run = build().run({})
        self.assertEqual(run.status, "suspended")
        resumed = build().resume(run.run_id, {"approved": "yes"})  # a fresh object, like a new process
        self.assertEqual(resumed.state["result"], "approved=yes")

    def test_finished_run_cannot_be_resumed_twice(self):
        f = Flow("t", self.store).then(lambda s: Suspend("wait")).then(add("x", 1))
        run = f.run({})
        f.resume(run.run_id, {})
        with self.assertRaises(FileNotFoundError):
            f.resume(run.run_id, {})

    def test_parallel_step_cannot_suspend(self):
        f = Flow("t", self.store).parallel(add("a", 1), lambda s: Suspend("no"))
        with self.assertRaises(TypeError):
            f.run({})

    def test_errors_propagate_and_are_marked_in_the_trace(self):
        def boom(s):
            raise ValueError("bad")
        f = Flow("t", self.store).then(boom)
        with self.assertRaises(ValueError):
            f.run({})

    def test_span_tree_lists_every_step(self):
        run = Flow("t", self.store).then(add("a", 1)).parallel(add("b", 2), add("c", 3)).run({})
        names = [line.split()[0] for line in run.trace.tree()]
        self.assertEqual(names, ["t", "set_a", "parallel", "set_b", "set_c"])


if __name__ == "__main__":
    unittest.main()
