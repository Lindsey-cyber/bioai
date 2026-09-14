from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from bioai_pipeline.ai import FastAssessmentBatch, OpenAIProcessor
from bioai_pipeline.config import Settings
from bioai_pipeline.models import PaperRecord


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    def parse(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        text_format = kwargs["text_format"]
        parsed = text_format.model_validate(
            {
                "assessments": [
                    {
                        "arxiv_id": "2609.00001",
                        "is_relevant": True,
                        "topics": ["neuroscience"],
                        "global_importance": 0.8,
                        "confidence": 0.9,
                        "reason_zh": "这项工作直接连接脑科学与机器学习。",
                    }
                ]
            }
        )
        return SimpleNamespace(
            output_parsed=parsed,
            model="gpt-5.6-luna",
            usage=SimpleNamespace(input_tokens=1000, output_tokens=500),
        )


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def make_paper() -> PaperRecord:
    return PaperRecord(
        id="paper-id",
        arxiv_id="2609.00001",
        latest_version=1,
        title="A foundation model for brain activity",
        abstract="We model neural activity with a transformer.",
        authors=(),
        categories=("q-bio.NC", "cs.LG"),
        published_at=datetime.now(timezone.utc),
        abstract_url="https://arxiv.org/abs/2609.00001",
        pdf_url="https://arxiv.org/pdf/2609.00001",
        geography_status="eligible",
        country_codes=("US",),
        processing_status="metadata_ready",
        source_metadata={},
    )


class OpenAIProcessorTest(unittest.TestCase):
    def test_fast_batch_uses_responses_structured_output(self) -> None:
        client = FakeClient()
        result = OpenAIProcessor(Settings.from_env(), client=client).assess_batch(
            [make_paper()]
        )

        self.assertIsInstance(result.value, FastAssessmentBatch)
        self.assertEqual(client.responses.kwargs["model"], "gpt-5.6-luna")
        self.assertEqual(client.responses.kwargs["reasoning"], {"effort": "none"})
        self.assertIs(client.responses.kwargs["store"], False)
        self.assertEqual(result.estimated_cost_usd, 0.0008)


if __name__ == "__main__":
    unittest.main()
