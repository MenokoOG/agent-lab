import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow as flowmod
from flow import Flow, Suspend


def a(s): return {"log": s.get("log", []) + ["a"], "x": 1}
def b(s): return {"log": s["log"] + ["b"], "y": s["x"] + 1}


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        flowmod.RUNS = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_chain_threads_results(self):
        run = Flow("t").then(a).then(b).run({})
        self.assertEqual((run.status, run.state["log"], run.state["y"]), ("done", ["a", "b"], 2))

    def test_parallel_runs_at_the_same_time_and_merges(self):
        barrier = threading.Barrier(3, timeout=2)  # sequential execution would time out here

        def p1(s): barrier.wait(); return {"p1": 1}
        def p2(s): barrier.wait(); return {"p2": 2}
        def p3(s): barrier.wait(); return {"p3": 3}

        run = Flow("t").parallel(p1, p2, p3).run({})
        self.assertEqual((run.state["p1"], run.state["p2"], run.state["p3"]), (1, 2, 3))

    def test_condition(self):
        def mark(s): return {"hit": True}
        yes = Flow("t").when(lambda s: s["go"], mark).run({"go": True})
        no = Flow("t").when(lambda s: s["go"], mark).run({"go": False})
        self.assertTrue(yes.state.get("hit"))
        self.assertNotIn("hit", no.state)

    def build(self):
        def ask(s): return Suspend("approve?")
        def finish(s): return {"result": "sent" if s.get("approved") else "dropped"}
        return Flow("t").then(a).then(ask).then(finish)

    def test_suspend_then_resume_in_a_fresh_flow_object(self):
        run = self.build().run({})
        self.assertEqual((run.status, run.reason), ("suspended", "approve?"))
        self.assertTrue((Path(self.tmp.name) / f"{run.run_id}.json").exists())
        resumed = self.build().resume(run.run_id, {"approved": True})  # new object, like a restarted process
        self.assertEqual((resumed.status, resumed.state["result"]), ("done", "sent"))
        self.assertEqual(resumed.state["log"], ["a"])  # step a did not run twice

    def test_parallel_cannot_suspend(self):
        def s1(s): return Suspend("no")
        with self.assertRaises(TypeError):
            Flow("t").parallel(s1).run({})

    def test_span_tree_shows_structure(self):
        def p1(s): return {"p1": 1}
        run = Flow("demo").then(a).parallel(p1).run({})
        lines = []
        run.trace.print_tree(out=lines.append)
        self.assertTrue(lines[0].startswith("demo"))
        self.assertTrue(any(l.startswith("  parallel") for l in lines))
        self.assertTrue(any(l.startswith("    p1") for l in lines))

    def test_step_error_is_recorded_and_raised(self):
        def boom(s): raise ValueError("bad")
        f = Flow("t").then(boom)
        with self.assertRaises(ValueError):
            f.run({})


class TriageShapeTests(unittest.TestCase):
    def test_each_step_has_at_most_one_llm_call(self):
        import llm
        import triage
        calls = []
        llm.FAKE = lambda body: (calls.append(1), llm.fake_text("yes"))[1]
        try:
            state = {"email": "x", "category": "billing", "urgent": True, "angry": False,
                     "refund": True, "flags": ["urgent"], "approved": "yes"}
            for step in (triage.classify, triage.check_urgent, triage.check_angry,
                         triage.check_refund, triage.draft_reply):
                calls.clear()
                step(state)
                self.assertLessEqual(len(calls), 1, step.__name__)
            calls.clear()
            triage.merge_flags(state)
            triage.ask_approval(state)
            self.assertEqual(len(calls), 0)
        finally:
            llm.FAKE = None


if __name__ == "__main__":
    unittest.main()
