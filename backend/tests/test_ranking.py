from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from bioai_pipeline.config import Settings
from bioai_pipeline.story_pipeline import _batched, _final_score, _freshness, _personal_relevance


class RankingTest(unittest.TestCase):
    def test_fast_candidates_are_split_into_small_stable_batches(self) -> None:
        values = list(range(32))

        self.assertEqual([len(batch) for batch in _batched(values, 15)], [15, 15, 2])

    def test_content_affinity_is_separate_from_explanation_depth(self) -> None:
        relevance = _personal_relevance(
            ["neuroscience", "protein design"],
            {"neuroscience": 0.9, "protein design": 0.7},
        )
        self.assertEqual(relevance, 0.8)

    def test_freshness_has_seven_day_half_life(self) -> None:
        now = datetime(2026, 9, 14, tzinfo=timezone.utc)
        self.assertEqual(_freshness(now - timedelta(days=7), now), 0.5)

    def test_default_ranking_weights(self) -> None:
        score = _final_score(
            Settings.from_env(),
            importance=0.8,
            personal=0.6,
            freshness=0.5,
            confidence=0.9,
        )
        self.assertEqual(score, 0.715)


if __name__ == "__main__":
    unittest.main()
