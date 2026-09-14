from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, replace

from bioai_pipeline.config import Settings
from bioai_pipeline.pipeline import run_arxiv_ingest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI x Bio ingestion pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest-arxiv", help="Fetch and normalize recent arXiv papers")
    ingest.add_argument("--dry-run", action="store_true", help="Do not write to PostgreSQL")
    ingest.add_argument("--lookback-hours", type=int)
    ingest.add_argument("--max-results-per-query", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_env()
    if args.lookback_hours is not None:
        settings = replace(settings, lookback_hours=args.lookback_hours)
    if args.max_results_per_query is not None:
        settings = replace(settings, max_results_per_query=args.max_results_per_query)

    if args.command == "ingest-arxiv":
        summary = run_arxiv_ingest(
            settings,
            dry_run=args.dry_run,
            trigger=os.getenv("PIPELINE_TRIGGER", "manual"),
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

