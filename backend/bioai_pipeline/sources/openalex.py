from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import replace
from difflib import SequenceMatcher
from typing import Any

from bioai_pipeline.models import OpenAlexMetadata


API_URL = "https://api.openalex.org/works"
AUTHORS_URL = "https://api.openalex.org/authors"
INSTITUTIONS_URL = "https://api.openalex.org/institutions"
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
        self._author_cache: dict[str, dict[str, Any] | None] = {}
        self._institution_cache: dict[str, dict[str, Any] | None] = {}
        self._works_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}

    def lookup_by_title(self, title: str) -> OpenAlexMetadata | None:
        params = {
            # OpenAlex treats punctuation such as a trailing question mark as
            # search syntax and can return HTTP 400. Reuse the plain title
            # normalization that also protects match verification.
            "search": normalize_title(title),
            "per_page": "5",
            "select": "id,title,doi,authorships,primary_location,publication_year,publication_date,topics",
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
        metadata = self._parse_match(match, similarity)
        # Profile enrichment is best-effort: a temporary profile endpoint error
        # must not discard a verified work match or block publication.
        try:
            return self.enrich_profiles(metadata)
        except OpenAlexError:
            return metadata

    def enrich_profiles(self, metadata: OpenAlexMetadata) -> OpenAlexMetadata:
        core_ids = {
            str(author.get("id"))
            for author in self._core_authors(metadata.authors)
            if author.get("id")
        }
        enriched_authors: list[dict[str, Any]] = []
        institution_ids: set[str] = set()
        current_topics = self._topic_names(metadata.raw.get("topics"))
        verified_profile_count = 0

        for author in metadata.authors:
            enriched = dict(author)
            author_id = str(author.get("id") or "")
            if author_id in core_ids:
                try:
                    profile = self._author_profile(author_id)
                except OpenAlexError:
                    profile = None
                if profile:
                    verified_profile_count += 1
                    current_institutions = self._compact_institutions(
                        profile.get("last_known_institutions") or []
                    )
                    try:
                        representative_works = self._representative_works(
                            author_id,
                            current_title=metadata.title,
                            current_topics=current_topics,
                        )
                    except OpenAlexError:
                        representative_works = []
                    enriched.update(
                        {
                            "name": profile.get("display_name") or author.get("name"),
                            "orcid": profile.get("orcid") or author.get("orcid"),
                            "profile_verified": True,
                            "openalex_url": profile.get("id") or author_id,
                            "research_topics": self._topic_names(profile.get("topics"))[:5],
                            "last_known_institutions": current_institutions,
                            "works_count": profile.get("works_count"),
                            "cited_by_count": profile.get("cited_by_count"),
                            "summary_stats": profile.get("summary_stats") or {},
                            "representative_works": representative_works,
                        }
                    )
                    if current_institutions:
                        enriched["institutions"] = current_institutions
            if author_id in core_ids:
                for institution in enriched.get("institutions") or []:
                    if institution.get("id"):
                        institution_ids.add(str(institution["id"]))
            enriched_authors.append(enriched)

        # Include institutions from every byline, but spend profile requests only
        # on institutions attached to the core authors shown in the UI.
        base_institutions = {
            str(institution.get("id")): dict(institution)
            for institution in metadata.institutions
            if institution.get("id")
        }
        for author in enriched_authors:
            for institution in [
                *(author.get("institutions") or []),
                *(author.get("last_known_institutions") or []),
            ]:
                if institution.get("id"):
                    base_institutions.setdefault(str(institution["id"]), dict(institution))

        enriched_institutions: list[dict[str, Any]] = []
        for institution in base_institutions.values():
            compact = dict(institution)
            institution_id = str(institution.get("id") or "")
            if institution_id in institution_ids:
                try:
                    profile = self._institution_profile(institution_id)
                except OpenAlexError:
                    profile = None
                if profile:
                    verified_profile_count += 1
                    compact.update(
                        {
                            "name": profile.get("display_name") or institution.get("name"),
                            "profile_verified": True,
                            "openalex_url": profile.get("id") or institution_id,
                            "homepage_url": profile.get("homepage_url"),
                            "image_url": profile.get("image_thumbnail_url") or profile.get("image_url"),
                            "location": profile.get("geo") or {},
                            "research_topics": self._topic_names(profile.get("topics"))[:5],
                            "works_count": profile.get("works_count"),
                            "cited_by_count": profile.get("cited_by_count"),
                        }
                    )
            enriched_institutions.append(compact)

        by_id = {str(item.get("id")): item for item in enriched_institutions if item.get("id")}
        for author in enriched_authors:
            author["institutions"] = [
                by_id.get(str(item.get("id")), item)
                for item in author.get("institutions") or []
            ]
            author["last_known_institutions"] = [
                by_id.get(str(item.get("id")), item)
                for item in author.get("last_known_institutions") or []
            ]

        raw = dict(metadata.raw)
        if verified_profile_count:
            raw["metadata_version"] = "profiles-v1"
        return replace(
            metadata,
            authors=tuple(enriched_authors),
            institutions=tuple(enriched_institutions),
            raw=raw,
        )

    @staticmethod
    def _core_authors(authors: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        if len(authors) <= 3:
            return authors
        selected: list[dict[str, Any]] = []
        for author in authors:
            if author.get("position") in {"first", "last"} or author.get("is_corresponding"):
                if author not in selected:
                    selected.append(author)
        for author in authors:
            if len(selected) >= 3:
                break
            if author not in selected:
                selected.append(author)
        return tuple(selected[:3])

    @staticmethod
    def _entity_id(value: str) -> str:
        return value.rstrip("/").rsplit("/", 1)[-1]

    def _url(self, base: str, entity_id: str | None = None, **params: str) -> str:
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{base}/{self._entity_id(entity_id)}" if entity_id else base
        return f"{url}?{urllib.parse.urlencode(params)}" if params else url

    def _author_profile(self, author_id: str) -> dict[str, Any] | None:
        key = self._entity_id(author_id)
        if key not in self._author_cache:
            payload = self._get(self._url(AUTHORS_URL, key))
            self._author_cache[key] = payload if payload.get("id") else None
        return self._author_cache[key]

    def _institution_profile(self, institution_id: str) -> dict[str, Any] | None:
        key = self._entity_id(institution_id)
        if key not in self._institution_cache:
            payload = self._get(self._url(INSTITUTIONS_URL, key))
            self._institution_cache[key] = payload if payload.get("id") else None
        return self._institution_cache[key]

    def _author_works(self, author_id: str, sort: str) -> list[dict[str, Any]]:
        key = (self._entity_id(author_id), sort)
        if key not in self._works_cache:
            payload = self._get(
                self._url(
                    API_URL,
                    filter=f"authorships.author.id:{key[0]}",
                    sort=sort,
                    per_page="15",
                    select="id,title,publication_year,publication_date,cited_by_count,doi,primary_location,topics",
                )
            )
            results = payload.get("results") or []
            self._works_cache[key] = [item for item in results if isinstance(item, dict)]
        return self._works_cache[key]

    def _representative_works(
        self,
        author_id: str,
        *,
        current_title: str,
        current_topics: list[str],
    ) -> list[dict[str, Any]]:
        cited = self._author_works(author_id, "cited_by_count:desc")
        recent = self._author_works(author_id, "publication_date:desc")
        works = {str(work.get("id")): work for work in [*cited, *recent] if work.get("id")}
        if not works:
            return []
        chosen: list[tuple[dict[str, Any], str]] = []

        def add(work: dict[str, Any] | None, reason: str) -> None:
            if work and all(item.get("id") != work.get("id") for item, _ in chosen):
                chosen.append((work, reason))

        add(cited[0] if cited else None, "highly_cited")
        add(recent[0] if recent else None, "current_direction")
        current_words = set(normalize_title(current_title).split())
        current_topic_set = {topic.casefold() for topic in current_topics}

        def relevance(work: dict[str, Any]) -> tuple[float, int]:
            work_words = set(normalize_title(str(work.get("title") or "")).split())
            union = current_words | work_words
            title_score = len(current_words & work_words) / len(union) if union else 0.0
            work_topics = {topic.casefold() for topic in self._topic_names(work.get("topics"))}
            topic_score = len(current_topic_set & work_topics) / max(1, len(current_topic_set))
            return (title_score * 0.7 + topic_score * 0.3, int(work.get("cited_by_count") or 0))

        add(max(works.values(), key=relevance), "related_to_story")
        for work in [*cited, *recent]:
            if len(chosen) >= 3:
                break
            add(work, "representative")

        return [self._compact_work(work, reason) for work, reason in chosen[:3]]

    @staticmethod
    def _topic_names(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [
            str(item.get("display_name"))
            for item in value
            if isinstance(item, dict) and item.get("display_name")
        ]

    @staticmethod
    def _compact_institutions(value: list[Any]) -> list[dict[str, Any]]:
        return [
            {
                "id": item.get("id"),
                "name": item.get("display_name"),
                "country_code": item.get("country_code"),
                "type": item.get("type"),
            }
            for item in value
            if isinstance(item, dict) and item.get("id")
        ]

    @staticmethod
    def _compact_work(work: dict[str, Any], reason: str) -> dict[str, Any]:
        location = work.get("primary_location") or {}
        return {
            "id": work.get("id"),
            "title": work.get("title"),
            "year": work.get("publication_year"),
            "publication_date": work.get("publication_date"),
            "cited_by_count": work.get("cited_by_count"),
            "doi": work.get("doi"),
            "url": work.get("doi") or location.get("landing_page_url") or work.get("id"),
            "selection_reason": reason,
        }

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
