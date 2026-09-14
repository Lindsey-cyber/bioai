from __future__ import annotations

import unittest
from datetime import date

from bioai_pipeline.filtering import classify_with_rules
from bioai_pipeline.sources.biorxiv import BiorxivClient


ITEM = {
    "title": "A foundation model for cellular phenotypes",
    "authors": "Example, A.; Researcher, B.",
    "author_corresponding": "Ada Example",
    "author_corresponding_institution": "Example University",
    "doi": "10.64898/2026.09.10.123456",
    "date": "2026-09-12",
    "version": "2",
    "type": "new results",
    "license": "cc_by",
    "category": "bioinformatics",
    "jatsxml": "https://www.biorxiv.org/example.source.xml",
    "abstract": "We use a transformer and machine learning to model cell morphology.",
}


class FakeBiorxivClient(BiorxivClient):
    def __init__(self) -> None:
        self.cursors: list[int] = []

    def _page(self, start_date: date, end_date: date, cursor: int):
        self.cursors.append(cursor)
        items = [dict(ITEM, doi=f"10.64898/test.{index}") for index in range(cursor, 65)]
        return {
            "messages": [{"status": "ok", "total": "65"}],
            "collection": items[:30],
        }


class BiorxivTest(unittest.TestCase):
    def test_parses_official_api_item(self) -> None:
        paper = BiorxivClient._parse_item(ITEM)

        self.assertEqual(paper.arxiv_id, "biorxiv:10.64898/2026.09.10.123456")
        self.assertEqual(paper.source, "biorxiv")
        self.assertEqual(paper.version, 2)
        self.assertEqual(len(paper.authors), 2)
        self.assertEqual(paper.source_metadata["corresponding_institution"], "Example University")
        self.assertEqual(paper.pdf_url, "https://www.biorxiv.org/content/10.64898/2026.09.10.123456v2.full.pdf")

    def test_reads_the_newest_window_when_capped(self) -> None:
        client = FakeBiorxivClient()
        papers = client.fetch_recent(
            start_date=date(2026, 9, 11),
            end_date=date(2026, 9, 14),
            max_results=40,
        )

        self.assertEqual(client.cursors, [0, 25, 55])
        self.assertEqual(len(papers), 40)
        self.assertEqual(papers[0].arxiv_id, "biorxiv:10.64898/test.25")
        self.assertEqual(papers[-1].arxiv_id, "biorxiv:10.64898/test.64")

    def test_biorxiv_context_counts_as_biological_evidence(self) -> None:
        paper = BiorxivClient._parse_item(
            dict(
                ITEM,
                title="A transformer for experimental phenotypes",
                abstract="We use machine learning to predict experimental outcomes.",
            )
        )
        result = classify_with_rules(paper)

        self.assertTrue(result.accepted)


if __name__ == "__main__":
    unittest.main()
