from __future__ import annotations

import unittest
from datetime import datetime, timezone

from bioai_pipeline.filtering import classify_with_rules
from bioai_pipeline.models import ArxivPaper


def paper(title: str, abstract: str, categories: tuple[str, ...]) -> ArxivPaper:
    now = datetime.now(timezone.utc)
    return ArxivPaper(
        arxiv_id="2609.00001",
        version=1,
        title=title,
        abstract=abstract,
        authors=(),
        categories=categories,
        primary_category=categories[0],
        published_at=now,
        updated_at=now,
        abstract_url="https://arxiv.org/abs/2609.00001",
        pdf_url="https://arxiv.org/pdf/2609.00001",
        doi=None,
        comment=None,
        query_name="test",
        raw_xml="<entry />",
    )


class FilteringTest(unittest.TestCase):
    def test_accepts_neuro_ai_paper(self) -> None:
        result = classify_with_rules(
            paper(
                "A foundation model for neural decoding",
                "We use a transformer to decode brain activity from fMRI.",
                ("q-bio.NC", "cs.LG"),
            )
        )
        self.assertTrue(result.accepted)
        self.assertIn("neuroscience", result.topics)
        self.assertIn("neuroimaging", result.topics)

    def test_rejects_non_biological_ml_paper(self) -> None:
        result = classify_with_rules(
            paper(
                "A transformer for database indexes",
                "A machine learning system for query optimization.",
                ("cs.LG",),
            )
        )
        self.assertFalse(result.accepted)


if __name__ == "__main__":
    unittest.main()

