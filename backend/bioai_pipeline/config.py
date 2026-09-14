from __future__ import annotations

import os
from dataclasses import dataclass


AI_TERMS = (
    'all:"machine learning"',
    'all:"deep learning"',
    'all:"foundation model"',
    'all:"language model"',
    "all:transformer",
    "all:generative",
    'all:"representation learning"',
    'all:"artificial intelligence"',
)

BIO_TERMS = (
    "all:protein",
    "all:enzyme",
    "all:molecule",
    "all:drug",
    "all:genome",
    "all:genomic",
    "all:gene",
    "all:cell",
    "all:clinical",
    "all:biomedical",
    "all:brain",
    "all:neuroscience",
    "all:neuroimaging",
    "all:connectome",
    "all:electrophysiology",
    'all:"brain-computer interface"',
)

Q_BIO_CATEGORIES = (
    "cat:q-bio.BM",
    "cat:q-bio.CB",
    "cat:q-bio.GN",
    "cat:q-bio.MN",
    "cat:q-bio.NC",
    "cat:q-bio.OT",
    "cat:q-bio.PE",
    "cat:q-bio.QM",
    "cat:q-bio.SC",
    "cat:q-bio.TO",
)

AI_CATEGORIES = (
    "cat:cs.AI",
    "cat:cs.LG",
    "cat:stat.ML",
    "cat:cs.CV",
)


def _or(values: tuple[str, ...]) -> str:
    return "(" + " OR ".join(values) + ")"


ARXIV_QUERIES = {
    "qbio_with_ai": f"{_or(Q_BIO_CATEGORIES)} AND {_or(AI_TERMS)}",
    "aiml_with_bio": f"{_or(AI_CATEGORIES)} AND {_or(BIO_TERMS)}",
}

ARXIV_RSS_FEEDS = {
    "qbio_with_ai": tuple(value.removeprefix("cat:") for value in Q_BIO_CATEGORIES),
    "aiml_with_bio": tuple(value.removeprefix("cat:") for value in AI_CATEGORIES),
}

# Product hard filter. Kept in configuration so the geography can change later.
DEFAULT_ALLOWED_COUNTRY_CODES = (
    "US,AL,AD,AT,BE,BG,BA,BY,CH,CY,CZ,DE,DK,EE,ES,FI,FR,GB,GR,HR,HU,IE,"
    "IS,IT,LI,LT,LU,LV,MC,MD,ME,MK,MT,NL,NO,PL,PT,RO,RS,SE,SI,SK,SM,UA,VA"
)


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    openai_api_key: str | None
    openalex_api_key: str | None
    fast_model: str
    deep_model: str
    reasoning_effort: str
    lookback_hours: int
    max_results_per_query: int
    max_sol_stories_per_day: int
    sol_max_input_tokens: int
    prompt_version: str
    arxiv_discovery_mode: str
    fast_reasoning_effort: str
    deep_reasoning_effort: str
    allowed_country_codes: frozenset[str]
    openalex_match_threshold: float
    openai_fast_input_cost_per_million: float
    openai_fast_output_cost_per_million: float
    openai_deep_input_cost_per_million: float
    openai_deep_output_cost_per_million: float
    rank_global_weight: float
    rank_personal_weight: float
    rank_freshness_weight: float
    rank_confidence_weight: float
    pdf_geography_fallback_limit: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openalex_api_key=os.getenv("OPENALEX_API_KEY"),
            fast_model=os.getenv("OPENAI_FAST_MODEL", "gpt-5.6-luna"),
            deep_model=os.getenv("OPENAI_DEEP_MODEL", "gpt-5.6-sol"),
            reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", "medium"),
            lookback_hours=int(os.getenv("ARXIV_LOOKBACK_HOURS", "72")),
            max_results_per_query=int(os.getenv("ARXIV_MAX_RESULTS_PER_QUERY", "300")),
            max_sol_stories_per_day=int(os.getenv("MAX_SOL_STORIES_PER_DAY", "6")),
            sol_max_input_tokens=int(os.getenv("SOL_MAX_INPUT_TOKENS", "18000")),
            prompt_version=os.getenv("PROMPT_VERSION", "story-v1"),
            arxiv_discovery_mode=os.getenv("ARXIV_DISCOVERY_MODE", "rss"),
            fast_reasoning_effort=os.getenv("OPENAI_FAST_REASONING_EFFORT", "none"),
            deep_reasoning_effort=os.getenv(
                "OPENAI_DEEP_REASONING_EFFORT",
                os.getenv("OPENAI_REASONING_EFFORT", "medium"),
            ),
            allowed_country_codes=frozenset(
                code.strip().upper()
                for code in os.getenv(
                    "ALLOWED_COUNTRY_CODES", DEFAULT_ALLOWED_COUNTRY_CODES
                ).split(",")
                if code.strip()
            ),
            openalex_match_threshold=float(os.getenv("OPENALEX_MATCH_THRESHOLD", "0.90")),
            openai_fast_input_cost_per_million=float(
                os.getenv("OPENAI_FAST_INPUT_COST_PER_MILLION", "0.20")
            ),
            openai_fast_output_cost_per_million=float(
                os.getenv("OPENAI_FAST_OUTPUT_COST_PER_MILLION", "1.20")
            ),
            openai_deep_input_cost_per_million=float(
                os.getenv("OPENAI_DEEP_INPUT_COST_PER_MILLION", "4.00")
            ),
            openai_deep_output_cost_per_million=float(
                os.getenv("OPENAI_DEEP_OUTPUT_COST_PER_MILLION", "20.00")
            ),
            rank_global_weight=float(os.getenv("RANK_GLOBAL_WEIGHT", "0.55")),
            rank_personal_weight=float(os.getenv("RANK_PERSONAL_WEIGHT", "0.30")),
            rank_freshness_weight=float(os.getenv("RANK_FRESHNESS_WEIGHT", "0.10")),
            rank_confidence_weight=float(os.getenv("RANK_CONFIDENCE_WEIGHT", "0.05")),
            pdf_geography_fallback_limit=int(
                os.getenv("PDF_GEOGRAPHY_FALLBACK_LIMIT", "12")
            ),
        )
