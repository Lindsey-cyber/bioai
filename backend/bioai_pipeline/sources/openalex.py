from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from typing import Any

from bioai_pipeline.models import OpenAlexMetadata


API_URL = "https://api.openalex.org/works"
USER_AGENT = "bioai-feed/0.1 (personal research reader; https://github.com/Lindsey-cyber/bioai)"


class OpenAlexError(RuntimeError):
    pass


def normalize_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_title(left), normalize_title(right)).ratio()


class OpenAlexClient:
    def __init__(self, api_key: str | None, match_threshold: float = 0.90):
        self.api_key = api_key
        self.match_threshold = match_threshold

    def lookup_by_title(self, title: str) -> OpenAlexMetadata | None:
        params = {
            "search": title,
            "per-page": "5",
            "select": "id,title,doi,authorships,primary_location",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        payload = self._get(f"{API_URL}?{urllib.parse.urlencode(params)}")
        results = payload.get("results") or []
        if not isinstance(results, list):
            raise OpenAlexError("OpenAlex response did not contain a results list")

        scored = [
            (title_similarity(title, str(result.get("title") or "")), result)
            for result in results
            if isinstance(result, dict)
        ]
        if not scored:
            return None
        similarity, match = max(scored, key=lambda item: item[0])
        if similarity < self.match_threshold:
            return None
        return self._parse_match(match, similarity)

    def _get(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.load(response)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if isinstance(exc, urllib.error.HTTPError) and exc.code < 500 and exc.code != 429:
                    break
                if attempt < 3:
                    time.sleep(2**attempt)
        raise OpenAlexError(f"OpenAlex request failed after retries: {last_error}")

    @staticmethod
    def _parse_match(match: dict[str, Any], similarity: float) -> OpenAlexMetadata:
        authors: list[dict[str, Any]] = []
        institutions_by_id: dict[str, dict[str, Any]] = {}

        for authorship in match.get("authorships") or []:
            author = authorship.get("author") or {}
            author_institutions: list[dict[str, Any]] = []
            for institution in authorship.get("institutions") or []:
                if not institution.get("id"):
                    continue
                compact = {
                    "id": institution.get("id"),
                    "name": institution.get("display_name"),
                    "country_code": institution.get("country_code"),
                    "type": institution.get("type"),
                }
                author_institutions.append(compact)
                institutions_by_id[str(compact["id"])] = compact
            authors.append(
                {
                    "id": author.get("id"),
                    "name": author.get("display_name"),
                    "orcid": author.get("orcid"),
                    "position": authorship.get("author_position"),
                    "is_corresponding": bool(authorship.get("is_corresponding")),
                    "institutions": author_institutions,
                    "raw_affiliations": authorship.get("raw_affiliation_strings") or [],
                }
            )

        institutions = tuple(institutions_by_id.values())
        country_codes = tuple(
            sorted(
                {
                    str(institution["country_code"]).upper()
                    for institution in institutions
                    if institution.get("country_code")
                }
            )
        )
        primary_location = match.get("primary_location")
        return OpenAlexMetadata(
            openalex_id=str(match.get("id") or ""),
            title=str(match.get("title") or ""),
            title_similarity=round(similarity, 4),
            authors=tuple(authors),
            institutions=institutions,
            country_codes=country_codes,
            primary_location=primary_location if isinstance(primary_location, dict) else None,
            doi=match.get("doi"),
            raw=match,
        )
