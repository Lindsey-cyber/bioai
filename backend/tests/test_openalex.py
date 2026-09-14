from __future__ import annotations

import unittest

from bioai_pipeline.sources.openalex import OpenAlexClient, title_similarity


MATCH = {
    "id": "https://openalex.org/W123",
    "title": "A Foundation Model for Brain Activity",
    "doi": "https://doi.org/10.1000/example",
    "primary_location": {"landing_page_url": "https://arxiv.org/abs/2609.1"},
    "authorships": [
        {
            "author_position": "first",
            "is_corresponding": True,
            "author": {
                "id": "https://openalex.org/A1",
                "display_name": "Ada Example",
                "orcid": "https://orcid.org/0000-0000-0000-0001",
            },
            "institutions": [
                {
                    "id": "https://openalex.org/I1",
                    "display_name": "Example University",
                    "country_code": "US",
                    "type": "education",
                }
            ],
            "raw_affiliation_strings": ["Example University, USA"],
        }
    ],
}


class OpenAlexTest(unittest.TestCase):
    def test_title_similarity_ignores_case_and_punctuation(self) -> None:
        score = title_similarity(
            "A foundation model: for brain activity",
            "A Foundation Model for Brain Activity",
        )
        self.assertEqual(score, 1.0)

    def test_parses_author_institution_and_country(self) -> None:
        metadata = OpenAlexClient._parse_match(MATCH, 0.99)
        self.assertEqual(metadata.openalex_id, "https://openalex.org/W123")
        self.assertEqual(metadata.authors[0]["name"], "Ada Example")
        self.assertTrue(metadata.authors[0]["is_corresponding"])
        self.assertEqual(metadata.institutions[0]["name"], "Example University")
        self.assertEqual(metadata.country_codes, ("US",))


if __name__ == "__main__":
    unittest.main()
