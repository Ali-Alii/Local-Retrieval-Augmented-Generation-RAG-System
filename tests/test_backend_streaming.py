import asyncio
import json
import unittest

from backend.app.streaming import FinalAnswerFilter, sse, stream_rag_answer


class UnsupportedEngine:
    @staticmethod
    def _unsupported_exact(_question: str) -> bool: return True


class StreamingTests(unittest.TestCase):
    def test_sse_serializes_json(self):
        event = sse("token", {"content": "hello"})
        self.assertTrue(event.startswith("event: token\n"))
        self.assertEqual(json.loads(event.split("data: ", 1)[1])["content"], "hello")

    def test_reasoning_filter_releases_only_final_answer(self):
        stream_filter = FinalAnswerFilter()
        self.assertEqual(stream_filter.feed("private reasoning"), [])
        self.assertEqual(stream_filter.feed("</think>\n\nFinal "), ["Final "])
        self.assertEqual(stream_filter.feed("answer"), ["answer"])
        self.assertEqual(stream_filter.finish(), [])

    def test_direct_answer_is_released_on_finish(self):
        stream_filter = FinalAnswerFilter()
        self.assertEqual(stream_filter.feed("Direct answer"), [])
        self.assertEqual(stream_filter.finish(), ["Direct answer"])

    def test_unsupported_question_streams_to_completion(self):
        async def collect(): return [item async for item in stream_rag_answer(UnsupportedEngine(), "live question")]
        events = asyncio.run(collect())
        self.assertIn("event: status", events[0])
        self.assertTrue(any("event: sources" in event for event in events))
        self.assertTrue(any("event: token" in event for event in events))
        self.assertIn("event: done", events[-1])


if __name__ == "__main__": unittest.main()
