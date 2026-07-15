import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rag.engine import Chunk, RAGEngine, _split, _tokens


class EngineTests(unittest.TestCase):
    def test_chunks_overlap_and_have_minimum_size(self):
        text = " ".join(f"word{i}" for i in range(900))
        chunks = list(_split(text, 100, 20))
        self.assertGreater(len(chunks), 9)
        self.assertEqual(chunks[0].split()[-20:], chunks[1].split()[:20])

    def test_retrieval_ranks_relevant_chunk(self):
        engine = RAGEngine()
        engine.chunks = [
            Chunk("a", "Enterprise assets inventory must be detailed and maintained.", "cis.pdf", 15, 0, _tokens("Enterprise assets inventory must be detailed and maintained.")),
            Chunk("b", "Email browsers and software protections.", "cis.pdf", 40, 1, _tokens("Email browsers and software protections.")),
        ]
        engine._reindex()
        result = engine.retrieve("How do I manage an enterprise asset inventory?", top_k=1)
        self.assertEqual(result[0]["id"], "a")

    def test_exact_control_title_beats_unrelated_control(self):
        engine = RAGEngine()
        rows = [
            ("right", "Control 01: Inventory and Control of Enterprise Assets. Actively manage all enterprise assets.", 17),
            ("wrong", "Control 08: Audit Log Management. Enterprise assets create access control logs.", 36),
        ]
        engine.chunks = [Chunk(i, text, "cis.pdf", page, n, _tokens(text)) for n, (i, text, page) in enumerate(rows)]
        engine._reindex()
        self.assertEqual(engine.retrieve("What is CIS Control 1?", top_k=1)[0]["id"], "right")

    def test_implementation_groups_section_wins(self):
        engine = RAGEngine()
        rows = [
            ("right", "Implementation Groups IG1 is essential cyber hygiene. IG2 handles sensitive data. IG3 supports critical services.", 15),
            ("wrong", "Development Group 3 develops application software for an enterprise.", 56),
        ]
        engine.chunks = [Chunk(i, text, "cis.pdf", page, n, _tokens(text)) for n, (i, text, page) in enumerate(rows)]
        engine._reindex()
        result = engine.retrieve("Give me the exact source pages used to explain Implementation Groups.", top_k=1)
        self.assertEqual(result[0]["id"], "right")

        shorthand = engine.retrieve("Explain the differences between IG1, IG2, and IG3.", top_k=1)
        self.assertEqual(shorthand[0]["id"], "right")

    def test_employee_offboarding_finds_access_revocation(self):
        engine = RAGEngine()
        rows = [
            ("right", "6.2 Establish an Access Revoking Process by disabling accounts immediately upon termination.", 32),
            ("wrong", "Keep third-party software components supported and up to date.", 58),
        ]
        engine.chunks = [Chunk(i, text, "cis.pdf", page, n, _tokens(text)) for n, (i, text, page) in enumerate(rows)]
        engine._reindex()
        result = engine.retrieve("A former employee's account is still active. What should we do?", top_k=1)
        self.assertEqual(result[0]["id"], "right")

        contractor = engine.retrieve(
            "A contractor has left the organization but their account still works. Which CIS Control and Safeguard apply?",
            top_k=1,
        )
        self.assertEqual(contractor[0]["id"], "right")

    def test_feedback_is_json_lines(self):
        engine = RAGEngine()
        with tempfile.TemporaryDirectory() as directory, patch("rag.engine.FEEDBACK_FILE", Path(directory) / "feedback.jsonl"):
            engine.feedback({"rating": "up", "question": "test"})
            self.assertIn('"rating": "up"', (Path(directory) / "feedback.jsonl").read_text())

    def test_unknown_year_abstains_without_sources(self):
        engine = RAGEngine()
        engine.chunks = [Chunk("a", "CIS Controls describe common cyber attacks.", "cis.pdf", 1, 0, _tokens("CIS Controls describe common cyber attacks."))]
        engine._reindex()
        result = engine.answer("What was the most common cyberattack in Lebanon in 2026?")
        self.assertEqual(result["mode"], "insufficient-evidence")
        self.assertEqual(result["sources"], [])

    def test_decimal_identifier_is_never_called_a_control(self):
        answer = RAGEngine._normalize_answer_terms("Control 06 applies. Control 06.2 revokes access.")
        self.assertEqual(answer, "Control 06 applies. Safeguard 6.2 revokes access.")


if __name__ == "__main__":
    unittest.main()
