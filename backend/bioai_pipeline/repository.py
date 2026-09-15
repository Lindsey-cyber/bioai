from __future__ import annotations

import hashlib
import json
import re
from contextlib import AbstractContextManager
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from bioai_pipeline.ai import FastAssessment, StoryExplanation
from bioai_pipeline.models import ArxivPaper, HeuristicResult, OpenAlexMetadata, PaperRecord


class Repository(AbstractContextManager["Repository"]):
    def __init__(self, database_url: str):
        # Each write is an idempotent upsert. Autocommit also guarantees that a
        # failed later item cannot erase the pipeline run/error record.
        self.connection = psycopg.connect(database_url, autocommit=True)

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.connection.close()

    def start_run(
        self,
        trigger: str,
        config: dict[str, Any],
        *,
        source: str = "arxiv",
    ) -> str:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pipeline_runs (source, trigger, status, config)
                VALUES (%s, %s, 'running', %s)
                RETURNING id::text
                """,
                (source, trigger, Jsonb(config)),
            )
            return cursor.fetchone()[0]

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        fetched_count: int,
        accepted_count: int,
        published_count: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost_usd: float = 0,
        error: str | None = None,
    ) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE pipeline_runs
                SET status = %s,
                    fetched_count = %s,
                    accepted_count = %s,
                    published_count = %s,
                    input_tokens = %s,
                    output_tokens = %s,
                    estimated_cost_usd = %s,
                    error = %s,
                    finished_at = now()
                WHERE id = %s
                """,
                (
                    status,
                    fetched_count,
                    accepted_count,
                    published_count,
                    input_tokens,
                    output_tokens,
                    estimated_cost_usd,
                    error,
                    run_id,
                ),
            )

    def save_raw(self, paper: ArxivPaper, run_id: str) -> None:
        payload = paper.raw_payload()
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO raw_items (
                    source, source_item_id, source_version, pipeline_run_id,
                    payload_sha256, raw_payload, processing_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'fetched')
                ON CONFLICT (source, source_item_id, source_version)
                DO UPDATE SET
                    last_seen_at = now(),
                    pipeline_run_id = EXCLUDED.pipeline_run_id,
                    payload_sha256 = EXCLUDED.payload_sha256,
                    raw_payload = EXCLUDED.raw_payload
                """,
                (
                    paper.source,
                    paper.arxiv_id,
                    paper.version,
                    run_id,
                    payload_hash,
                    Jsonb(payload),
                ),
            )

    def save_raw_batch(self, papers: list[ArxivPaper], run_id: str) -> None:
        rows: list[tuple[object, ...]] = []
        for paper in papers:
            payload = paper.raw_payload()
            payload_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            rows.append(
                (
                    paper.source,
                    paper.arxiv_id,
                    paper.version,
                    run_id,
                    payload_hash,
                    Jsonb(payload),
                )
            )
        if not rows:
            return
        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO raw_items (
                    source, source_item_id, source_version, pipeline_run_id,
                    payload_sha256, raw_payload, processing_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'fetched')
                ON CONFLICT (source, source_item_id, source_version)
                DO UPDATE SET
                    last_seen_at = now(),
                    pipeline_run_id = EXCLUDED.pipeline_run_id,
                    payload_sha256 = EXCLUDED.payload_sha256,
                    raw_payload = EXCLUDED.raw_payload
                """,
                rows,
            )

    def upsert_paper(self, paper: ArxivPaper, result: HeuristicResult) -> None:
        authors = [
            {"name": author.name, "affiliation": author.affiliation}
            for author in paper.authors
        ]
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO papers (
                    arxiv_id, latest_version, doi, title, abstract, authors,
                    categories, primary_category, published_at, source_updated_at,
                    abstract_url, pdf_url, source_comment, topics,
                    rule_relevance, processing_status, source_metadata
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, 'rule_accepted', %s
                )
                ON CONFLICT (arxiv_id)
                DO UPDATE SET
                    latest_version = GREATEST(papers.latest_version, EXCLUDED.latest_version),
                    doi = COALESCE(EXCLUDED.doi, papers.doi),
                    title = EXCLUDED.title,
                    abstract = EXCLUDED.abstract,
                    authors = CASE
                        WHEN papers.source_metadata ? 'openalex' THEN papers.authors
                        ELSE EXCLUDED.authors
                    END,
                    categories = EXCLUDED.categories,
                    primary_category = EXCLUDED.primary_category,
                    source_updated_at = EXCLUDED.source_updated_at,
                    abstract_url = EXCLUDED.abstract_url,
                    pdf_url = EXCLUDED.pdf_url,
                    source_comment = EXCLUDED.source_comment,
                    topics = CASE
                        WHEN papers.source_metadata ? 'fast_assessment' THEN papers.topics
                        ELSE EXCLUDED.topics
                    END,
                    rule_relevance = EXCLUDED.rule_relevance,
                    source_metadata = papers.source_metadata || EXCLUDED.source_metadata,
                    updated_at = now()
                """,
                (
                    paper.arxiv_id,
                    paper.version,
                    paper.doi,
                    paper.title,
                    paper.abstract,
                    Jsonb(authors),
                    list(paper.categories),
                    paper.primary_category,
                    paper.published_at,
                    paper.updated_at,
                    paper.abstract_url,
                    paper.pdf_url,
                    paper.comment,
                    list(result.topics),
                    result.relevance,
                    Jsonb(
                        {
                            "source": paper.source,
                            **(paper.source_metadata or {}),
                            "query_name": paper.query_name,
                            "matched_ai_terms": result.matched_ai_terms,
                            "matched_bio_terms": result.matched_bio_terms,
                        }
                    ),
                ),
            )

    def list_processing_candidates(self, limit: int) -> list[PaperRecord]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id::text, arxiv_id, latest_version, title, abstract, authors,
                       categories, published_at, abstract_url, pdf_url,
                       geography_status, country_codes, processing_status,
                       source_metadata
                FROM papers
                WHERE processing_status IN (
                    'rule_accepted', 'metadata_unresolved', 'metadata_ready',
                    'deep_pending', 'processing_failed'
                )
                ORDER BY
                    (topics && ARRAY[
                        'neuroscience', 'neuroimaging', 'brain-computer interfaces'
                    ]::text[]) DESC,
                    rule_relevance DESC NULLS LAST,
                    published_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [self._paper_record(row) for row in cursor.fetchall()]

    def list_deep_candidates(self, limit: int) -> list[PaperRecord]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id::text, arxiv_id, latest_version, title, abstract, authors,
                       categories, published_at, abstract_url, pdf_url,
                       geography_status, country_codes, processing_status,
                       source_metadata
                FROM papers
                WHERE processing_status = 'deep_pending'
                   OR (
                       processing_status = 'processing_failed'
                       AND geography_status = 'eligible'
                       AND source_metadata ? 'fast_assessment'
                   )
                ORDER BY global_importance DESC NULLS LAST, published_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [self._paper_record(row) for row in cursor.fetchall()]

    @staticmethod
    def _paper_record(row: tuple[Any, ...]) -> PaperRecord:
        return PaperRecord(
            id=row[0],
            arxiv_id=row[1],
            latest_version=row[2],
            title=row[3],
            abstract=row[4],
            authors=tuple(row[5] or []),
            categories=tuple(row[6] or []),
            published_at=row[7],
            abstract_url=row[8],
            pdf_url=row[9],
            geography_status=row[10],
            country_codes=tuple(row[11] or []),
            processing_status=row[12],
            source_metadata=row[13] or {},
        )

    def save_openalex_metadata(
        self,
        paper_id: str,
        metadata: OpenAlexMetadata | None,
        allowed_country_codes: frozenset[str],
    ) -> str:
        if metadata is None:
            geography_status = "unknown"
            processing_status = "metadata_unresolved"
            countries: list[str] = []
            patch = {"openalex_status": "not_found"}
            authors = None
            institutions = None
            doi = None
        else:
            countries = list(metadata.country_codes)
            if not countries:
                geography_status = "unknown"
                processing_status = "metadata_unresolved"
            elif allowed_country_codes.intersection(countries):
                geography_status = "eligible"
                processing_status = "metadata_ready"
            else:
                geography_status = "ineligible"
                processing_status = "geography_ineligible"
            patch = {
                "openalex_status": "matched",
                "openalex": {
                    "id": metadata.openalex_id,
                    "title": metadata.title,
                    "title_similarity": metadata.title_similarity,
                    "authors": metadata.authors,
                    "institutions": metadata.institutions,
                    "primary_location": metadata.primary_location,
                },
            }
            authors = list(metadata.authors)
            institutions = list(metadata.institutions)
            doi = metadata.doi

        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE papers
                SET authors = COALESCE(%s, authors),
                    affiliations = COALESCE(%s, affiliations),
                    doi = COALESCE(papers.doi, %s),
                    geography_status = %s,
                    country_codes = %s,
                    processing_status = %s,
                    processing_error = NULL,
                    source_metadata = source_metadata || %s,
                    updated_at = now()
                WHERE id = %s
                """,
                (
                    Jsonb(authors) if authors is not None else None,
                    Jsonb(institutions) if institutions is not None else None,
                    doi,
                    geography_status,
                    countries,
                    processing_status,
                    Jsonb(patch),
                    paper_id,
                ),
            )
        return geography_status

    def save_fast_assessment(
        self,
        paper_id: str,
        assessment: FastAssessment,
        *,
        model: str,
        prompt_version: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
    ) -> None:
        status = "deep_pending" if assessment.is_relevant else "fast_rejected"
        patch = {
            "fast_assessment": assessment.model_dump(mode="json"),
            "fast_model": model,
            "fast_prompt_version": prompt_version,
            "fast_usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": estimated_cost_usd,
            },
        }
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE papers
                SET topics = %s,
                    ai_relevance = %s,
                    global_importance = %s,
                    confidence = %s,
                    processing_status = %s,
                    processing_error = NULL,
                    source_metadata = source_metadata || %s,
                    updated_at = now()
                WHERE id = %s
                """,
                (
                    list(assessment.topics),
                    1.0 if assessment.is_relevant else 0.0,
                    assessment.global_importance,
                    assessment.confidence,
                    status,
                    Jsonb(patch),
                    paper_id,
                ),
            )

    def save_ai_geography(
        self,
        paper_id: str,
        assessment: FastAssessment,
        allowed_country_codes: frozenset[str],
    ) -> str:
        countries = sorted({code.upper() for code in assessment.country_codes})
        if not countries:
            geography_status = "unknown"
            processing_status = "metadata_unresolved"
        elif allowed_country_codes.intersection(countries):
            geography_status = "eligible"
            processing_status = "metadata_ready"
        else:
            geography_status = "ineligible"
            processing_status = "geography_ineligible"
        patch = {
            "pdf_geography": {
                "country_codes": countries,
                "evidence": assessment.geography_evidence,
            }
        }
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE papers
                SET geography_status = %s,
                    country_codes = %s,
                    processing_status = %s,
                    processing_error = NULL,
                    source_metadata = source_metadata || %s,
                    updated_at = now()
                WHERE id = %s
                """,
                (
                    geography_status,
                    countries,
                    processing_status,
                    Jsonb(patch),
                    paper_id,
                ),
            )
        return geography_status

    def save_pdf_text(
        self,
        paper: PaperRecord,
        run_id: str,
        text: str,
        *,
        scope: str = "full_text",
    ) -> None:
        source = str(paper.source_metadata.get("source") or "arxiv")
        payload = {"url": paper.pdf_url, "text": text, "scope": scope}
        payload_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO raw_items (
                    source, source_item_id, source_version, pipeline_run_id,
                    payload_sha256, raw_payload, processing_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'fetched')
                ON CONFLICT (source, source_item_id, source_version)
                DO UPDATE SET
                    last_seen_at = now(),
                    pipeline_run_id = EXCLUDED.pipeline_run_id,
                    payload_sha256 = EXCLUDED.payload_sha256,
                    raw_payload = EXCLUDED.raw_payload,
                    processing_status = 'fetched',
                    processing_error = NULL
                """,
                (
                    f"{source}_article_text",
                    paper.arxiv_id,
                    paper.latest_version,
                    run_id,
                    payload_hash,
                    Jsonb(payload),
                ),
            )

    def preference_topic_affinity(self) -> dict[str, float]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT topic_affinity FROM preference_profile WHERE id = 'owner'"
            )
            row = cursor.fetchone()
        return {key: float(value) for key, value in (row[0] if row else {}).items()}

    def publish_story(
        self,
        paper: PaperRecord,
        assessment: FastAssessment,
        explanation: StoryExplanation,
        *,
        model: str,
        prompt_version: str,
        input_tokens: int,
        output_tokens: int,
        estimated_cost_usd: float,
        personal_relevance: float,
        freshness: float,
        final_score: float,
    ) -> str:
        source = str(paper.source_metadata.get("source") or "arxiv").lower()
        source_label = "bioRxiv" if source == "biorxiv" else "arXiv"
        source_external_id = str(
            paper.source_metadata.get("source_external_id") or paper.arxiv_id
        )
        slug_id = re.sub(r"[^a-z0-9]+", "-", source_external_id.lower()).strip("-")
        slug = f"{source}-{slug_id}"
        content = {
            "title_zh": explanation.title_zh,
            "sections": explanation.sections.model_dump(mode="json"),
        }
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO stories (
                        paper_id, slug, status, global_importance,
                        personal_relevance, freshness, confidence, final_score,
                        why_recommended, published_at
                    )
                    VALUES (%s, %s, 'published', %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (paper_id)
                    DO UPDATE SET
                        status = 'published',
                        global_importance = EXCLUDED.global_importance,
                        personal_relevance = EXCLUDED.personal_relevance,
                        freshness = EXCLUDED.freshness,
                        confidence = EXCLUDED.confidence,
                        final_score = EXCLUDED.final_score,
                        why_recommended = EXCLUDED.why_recommended,
                        published_at = COALESCE(stories.published_at, now()),
                        updated_at = now()
                    RETURNING id::text
                    """,
                    (
                        paper.id,
                        slug,
                        assessment.global_importance,
                        personal_relevance,
                        freshness,
                        assessment.confidence,
                        final_score,
                        assessment.reason_zh,
                        paper.published_at,
                    ),
                )
                story_id = cursor.fetchone()[0]
                cursor.execute(
                    """
                    INSERT INTO story_sources (
                        story_id, source_type, label, url, external_id, is_original
                    )
                    VALUES (%s, %s, %s, %s, %s, true)
                    ON CONFLICT (story_id, url)
                    DO UPDATE SET is_original = true, label = EXCLUDED.label,
                                  source_type = EXCLUDED.source_type
                    """,
                    (
                        story_id,
                        source,
                        source_label,
                        paper.abstract_url,
                        source_external_id,
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO explanations (
                        story_id, model, prompt_version, content, limitations,
                        terminology, input_tokens, output_tokens, estimated_cost_usd
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (story_id, model, prompt_version)
                    DO UPDATE SET
                        content = EXCLUDED.content,
                        limitations = EXCLUDED.limitations,
                        terminology = EXCLUDED.terminology,
                        input_tokens = EXCLUDED.input_tokens,
                        output_tokens = EXCLUDED.output_tokens,
                        estimated_cost_usd = EXCLUDED.estimated_cost_usd
                    """,
                    (
                        story_id,
                        model,
                        prompt_version,
                        Jsonb(content),
                        Jsonb(explanation.limitations),
                        Jsonb([term.model_dump(mode="json") for term in explanation.terminology]),
                        input_tokens,
                        output_tokens,
                        estimated_cost_usd,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE papers
                    SET processing_status = 'published', processing_error = NULL,
                        updated_at = now()
                    WHERE id = %s
                    """,
                    (paper.id,),
                )
        return story_id

    def mark_processing_error(self, paper_id: str, error: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE papers
                SET processing_status = 'processing_failed',
                    processing_error = %s,
                    updated_at = now()
                WHERE id = %s
                """,
                (error[:4000], paper_id),
            )
