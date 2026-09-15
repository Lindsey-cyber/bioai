from __future__ import annotations

import unittest
from datetime import date

from bioai_pipeline.filtering import classify_with_rules
from bioai_pipeline.sources.biorxiv import BiorxivClient, CrossrefBiorxivClient


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

CROSSREF_ITEM = {
    "DOI": "10.64898/2026.09.10.654321",
    "title": ["A neural network for single-cell phenotypes"],
    "abstract": "<jats:p>We use a <jats:italic>transformer</jats:italic> model.</jats:p>",
    "published": {"date-parts": [[2026, 9, 12]]},
    "institution": [{"name": "bioRxiv"}],
    "group-title": "Bioinformatics",
    "subtype": "preprint",
    "author": [
        {
            "given": "Ada",
            "family": "Example",
            "affiliation": [{"name": "Example University"}],
        }
    ],
    "resource": {
        "primary": {
            "URL": "https://www.biorxiv.org/lookup/doi/10.64898/2026.09.10.654321"
        }
    },
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


class IncompleteItemClient(BiorxivClient):
    def _page(self, start_date: date, end_date: date, cursor: int):
        return {
            "messages": [{"status": "ok", "total": "2"}],
            "collection": [{"title": "Withdrawn record"}, ITEM],
        }


class LaterPageTimeoutClient(BiorxivClient):
    def _page(self, start_date: date, end_date: date, cursor: int):
        if cursor:
            from bioai_pipeline.sources.biorxiv import BiorxivError

            raise BiorxivError("timed out")
        return {
            "messages": [{"status": "ok", "total": "60"}],
            "collection": [dict(ITEM, doi=f"10.64898/partial.{index}") for index in range(30)],
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

    def test_skips_incomplete_records_without_stopping_the_batch(self) -> None:
        papers = IncompleteItemClient().fetch_recent(
            start_date=date(2026, 9, 11),
            end_date=date(2026, 9, 14),
            max_results=10,
        )

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].source, "biorxiv")

    def test_keeps_completed_pages_when_a_later_page_times_out(self) -> None:
        papers = LaterPageTimeoutClient().fetch_recent(
            start_date=date(2026, 9, 11),
            end_date=date(2026, 9, 14),
            max_results=60,
        )

        self.assertEqual(len(papers), 30)

    def test_parses_crossref_fallback_item(self) -> None:
        paper = CrossrefBiorxivClient._parse_item(CROSSREF_ITEM)

        self.assertEqual(paper.source, "biorxiv")
        self.assertEqual(paper.abstract, "We use a transformer model.")
        self.assertEqual(paper.authors[0].affiliation, "Example University")
        self.assertEqual(
            paper.source_metadata["metadata_provider"],
            "crossref_fallback",
        )

    def test_crossref_filter_rejects_other_preprint_servers(self) -> None:
        medrxiv = dict(CROSSREF_ITEM, institution=[{"name": "medRxiv"}])
        medrxiv["resource"] = {
            "primary": {"URL": "https://www.medrxiv.org/lookup/doi/example"}
        }

        self.assertFalse(CrossrefBiorxivClient._is_biorxiv(medrxiv))


if __name__ == "__main__":
    unittest.main()
