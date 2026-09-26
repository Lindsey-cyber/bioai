from __future__ import annotations

import unittest
import urllib.parse

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

    def test_search_normalizes_openalex_query_syntax(self) -> None:
        class CapturingClient(OpenAlexClient):
            requested_url = ""

            def _get(self, url: str):
                self.requested_url = url
                return {"results": []}

        client = CapturingClient(None)
        client.lookup_by_title("Is AI Capable of Real-World Drug Discovery?")
        query = urllib.parse.parse_qs(urllib.parse.urlparse(client.requested_url).query)

        self.assertEqual(
            query["search"],
            ["is ai capable of real world drug discovery"],
        )

    def test_enrichment_uses_ids_and_selects_three_distinct_works(self) -> None:
        class FixtureClient(OpenAlexClient):
            requested_urls: list[str]

            def __init__(self) -> None:
                super().__init__("test-key")
                self.requested_urls = []

            def _get(self, url: str):
                self.requested_urls.append(url)
                if "/authors/A1" in url:
                    return {
                        "id": "https://openalex.org/A1",
                        "display_name": "Ada Example",
                        "orcid": "https://orcid.org/0000-0000-0000-0001",
                        "last_known_institutions": MATCH["authorships"][0]["institutions"],
                        "topics": [{"display_name": "Neural Engineering"}],
                        "works_count": 12,
                        "cited_by_count": 250,
                    }
                if "/institutions/I1" in url:
                    return {
                        "id": "https://openalex.org/I1",
                        "display_name": "Example University",
                        "homepage_url": "https://example.edu",
                        "geo": {"city": "Boston", "country": "United States"},
                        "topics": [{"display_name": "Neural Engineering"}],
                    }
                if "sort=cited_by_count%3Adesc" in url:
                    return {"results": [
                        {"id": "W1", "title": "Landmark method", "publication_year": 2020, "cited_by_count": 200},
                        {"id": "W2", "title": "Brain activity model", "publication_year": 2025, "cited_by_count": 20},
                    ]}
                if "sort=publication_date%3Adesc" in url:
                    return {"results": [
                        {"id": "W3", "title": "A Foundation Model for Brain Activity", "publication_year": 2026, "publication_date": "2026-09-01", "cited_by_count": 2},
                        {"id": "W2", "title": "Brain activity model", "publication_year": 2025, "cited_by_count": 20},
                    ]}
                raise AssertionError(url)

        metadata = OpenAlexClient._parse_match({**MATCH, "topics": [{"display_name": "Neural Engineering"}]}, 0.99)
        client = FixtureClient()
        enriched = client.enrich_profiles(metadata)

        author = enriched.authors[0]
        self.assertTrue(author["profile_verified"])
        self.assertEqual(len(author["representative_works"]), 3)
        self.assertEqual(enriched.institutions[0]["location"]["city"], "Boston")
        self.assertEqual(enriched.raw["metadata_version"], "profiles-v1")
        self.assertTrue(all("A1" in url or "I1" in url for url in client.requested_urls))


if __name__ == "__main__":
    unittest.main()
