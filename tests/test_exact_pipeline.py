import unittest
from types import SimpleNamespace

from langchain_core.documents import Document

from rag.exact_pipeline import chunk_report, element_report


class FakeElement:
    def __init__(self, text, page):
        self.text = text
        self.metadata = SimpleNamespace(page_number=page)

    def __str__(self):
        return self.text


class ExactPipelineTests(unittest.TestCase):
    def test_element_report_retains_page_statistics(self):
        report = element_report([FakeElement("alpha", 1), FakeElement("beta", 2)])
        self.assertEqual(report["elements"], 2)
        self.assertEqual(report["pages"], 2)
        self.assertEqual(report["characters"], 9)

    def test_chunk_report_compares_methods(self):
        report = chunk_report({"by_title": [Document(page_content="abc"), Document(page_content="12345")]})
        self.assertEqual(report["by_title"]["chunks"], 2)
        self.assertEqual(report["by_title"]["maximum_characters"], 5)


if __name__ == "__main__":
    unittest.main()
