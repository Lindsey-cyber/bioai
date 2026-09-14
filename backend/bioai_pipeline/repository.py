from __future__ import annotations

import hashlib
import json
from contextlib import AbstractContextManager
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from bioai_pipeline.models import ArxivPaper, HeuristicResult


class Repository(AbstractContextManager["Repository"]):
    def __init__(self, database_url: str):
        # Each write is an idempotent upsert. Autocommit also guarantees that a
        # failed later item cannot erase the pipeline run/error record.
        self.connection = psycopg.connect(database_url, autocommit=True)

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.connection.close()

    def start_run(self, trigger: str, config: dict[str, Any]) -> str:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pipeline_runs (source, trigger, status, config)
                VALUES ('arxiv', %s, 'running', %s)
                RETURNING id::text
                """,
                (trigger, Jsonb(config)),
            )
            return cursor.fetchone()[0]

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        fetched_count: int,
        accepted_count: int,
        error: str | None = None,
    ) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE pipeline_runs
                SET status = %s,
                    fetched_count = %s,
                    accepted_count = %s,
                    error = %s,
                    finished_at = now()
                WHERE id = %s
                """,
                (status, fetched_count, accepted_count, error, run_id),
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
                VALUES ('arxiv', %s, %s, %s, %s, %s, 'fetched')
                ON CONFLICT (source, source_item_id, source_version)
                DO UPDATE SET
                    last_seen_at = now(),
                    pipeline_run_id = EXCLUDED.pipeline_run_id,
                    payload_sha256 = EXCLUDED.payload_sha256,
                    raw_payload = EXCLUDED.raw_payload
                """,
                (
                    paper.arxiv_id,
                    paper.version,
                    run_id,
                    payload_hash,
                    Jsonb(payload),
                ),
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
                    authors = EXCLUDED.authors,
                    categories = EXCLUDED.categories,
                    primary_category = EXCLUDED.primary_category,
                    source_updated_at = EXCLUDED.source_updated_at,
                    abstract_url = EXCLUDED.abstract_url,
                    pdf_url = EXCLUDED.pdf_url,
                    source_comment = EXCLUDED.source_comment,
                    topics = EXCLUDED.topics,
                    rule_relevance = EXCLUDED.rule_relevance,
                    source_metadata = EXCLUDED.source_metadata,
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
                            "query_name": paper.query_name,
                            "matched_ai_terms": result.matched_ai_terms,
                            "matched_bio_terms": result.matched_bio_terms,
                        }
                    ),
                ),
            )
