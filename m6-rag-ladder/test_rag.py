import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm
import rung2_tools
import rung3_rag
from corpus_io import load_docs
from ladder import QUESTIONS, correct
from rung3_rag import Index, chunk, cosine, words


class RagTests(unittest.TestCase):
    def tearDown(self):
        llm.FAKE = None

    def test_chunks_overlap_and_cover_the_text(self):
        text = "x" * 500
        chunks = chunk(text, size=200, overlap=40)
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0][-40:], chunks[1][:40])

    def test_cosine(self):
        self.assertAlmostEqual(cosine({"a": 1}, {"a": 2}), 1.0)
        self.assertEqual(cosine({"a": 1}, {"b": 1}), 0.0)

    def test_retrieval_finds_the_right_file_for_text_questions(self):
        index = Index(load_docs())
        expect = {
            "What is the minimum password length?": "security.txt",
            "How much is the home-office stipend?": "remote.txt",
            "How many paid holidays does the company observe?": "holidays.txt",
            "How many vacation days do full-time employees get per year?": "vacation.txt",
        }
        for q, fname in expect.items():
            self.assertIn(fname, [n for n, _ in index.top_k(q, k=3)], q)

    def test_retrieval_cannot_do_arithmetic_which_is_the_point_of_rung_2(self):
        index = Index(load_docs())
        hits = [c for _, c in index.top_k("What is the total headcount across all locations?", k=3)]
        self.assertNotIn("120", " ".join(hits))  # the total is never in the text

    def test_tools_answer_the_count_questions_exactly(self):
        self.assertEqual(rung2_tools.total_headcount(), "120")
        self.assertTrue(rung2_tools.largest_location().startswith("Seattle"))
        self.assertEqual(len(json.loads(rung2_tools.locations_above("25"))), 3)

    def test_every_question_has_a_checkable_answer(self):
        self.assertEqual(len(QUESTIONS), 10)
        self.assertEqual(sum(q["kind"] == "count" for q in QUESTIONS), 3)
        self.assertTrue(correct("It is 14.", QUESTIONS[2]["must"]))
        self.assertFalse(correct("It is 140.", QUESTIONS[2]["must"]))

    def test_rerank_falls_back_to_original_order(self):
        hits = [("a", "one"), ("b", "two"), ("c", "three")]
        llm.FAKE = lambda body: llm.fake_text("no numbers here")
        self.assertEqual(rung3_rag.rerank("q", hits), hits)
        llm.FAKE = lambda body: llm.fake_text("2, 0, 1")
        self.assertEqual(rung3_rag.rerank("q", hits), [hits[2], hits[0], hits[1]])

    def test_answer_builds_a_prompt_from_retrieved_chunks(self):
        llm.FAKE = llm.scripted(llm.fake_text("14", tokens=50))
        rung3_rag._INDEX = None
        text, tokens = rung3_rag.answer("What is the minimum password length?")
        self.assertEqual((text, tokens), ("14", 50))
        prompt = llm.FAKE.bodies[0]["messages"][0]["content"]
        self.assertIn("security.txt", prompt)


if __name__ == "__main__":
    unittest.main()
