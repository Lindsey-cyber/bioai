from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, time as datetime_time, timezone

from bioai_pipeline.models import ArxivPaper, Author
from bioai_pipeline.sources.arxiv import USER_AGENT


EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

AI_QUERY = " OR ".join(
    (
        '"artificial intelligence"[Title/Abstract]',
        '"machine learning"[Title/Abstract]',
        '"deep learning"[Title/Abstract]',
        '"foundation model"[Title/Abstract]',
        '"language model"[Title/Abstract]',
        'transformer[Title/Abstract]',
        'generative[Title/Abstract]',
        '"representation learning"[Title/Abstract]',
    )
)

MONTHS = {
    name.lower(): index
    for index, name in enumerate(
        (
            "",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        )
    )
    if name
}


class PubmedError(RuntimeError):
    pass


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


class PubmedClient:
    def __init__(
        self,
        *,
        email: str,
        api_key: str | None = None,
        request_timeout: int = 30,
        max_attempts: int = 3,
    ):
        self.email = email
        self.api_key = api_key
        self.request_timeout = request_timeout
        self.max_attempts = max(1, max_attempts)

    def fetch_recent(
        self,
        *,
        start_date: date,
        end_date: date,
        max_results: int,
    ) -> list[ArxivPaper]:
        ids = self._search(start_date, end_date, max_results)
        if not ids:
            return []
        xml = self._request(
            "efetch.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(ids),
                "rettype": "abstract",
                "retmode": "xml",
            },
        )
        root = ET.fromstring(xml)
        papers: list[ArxivPaper] = []
        for article in root.findall("./PubmedArticle"):
            try:
                papers.append(self._parse_article(article))
            except (PubmedError, TypeError, ValueError):
                continue
        return papers

    def _search(
        self,
        start_date: date,
        end_date: date,
        max_results: int,
    ) -> list[str]:
        date_query = (
            f'("{start_date:%Y/%m/%d}"[Date - Publication] : '
            f'"{end_date:%Y/%m/%d}"[Date - Publication])'
        )
        payload = json.loads(
            self._request(
                "esearch.fcgi",
                {
                    "db": "pubmed",
                    "term": f"({AI_QUERY}) AND {date_query}",
                    "retmode": "json",
                    "retmax": str(max_results),
                    "sort": "pub date",
                },
            )
        )
        return [str(value) for value in payload.get("esearchresult", {}).get("idlist") or []]

    def _request(self, endpoint: str, params: dict[str, str]) -> bytes:
        request_params = {
            **params,
            "tool": "bioai-feed",
            "email": self.email,
        }
        if self.api_key:
            request_params["api_key"] = self.api_key
        url = f"{EUTILS_URL}/{endpoint}?{urllib.parse.urlencode(request_params)}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/xml, application/json"},
        )
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
                    return response.read()
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if (
                    isinstance(exc, urllib.error.HTTPError)
                    and exc.code < 500
                    and exc.code != 429
                ):
                    break
                if attempt < self.max_attempts - 1:
                    time.sleep(2**attempt)
        raise PubmedError(f"PubMed E-utilities request failed after retries: {last_error}")

    @staticmethod
    def _parse_article(article: ET.Element) -> ArxivPaper:
        citation = article.find("./MedlineCitation")
        if citation is None:
            raise PubmedError("PubMed record is missing MedlineCitation")
        pmid = _text(citation.find("./PMID"))
        if not pmid:
            raise PubmedError("PubMed record is missing PMID")
        journal_article = citation.find("./Article")
        if journal_article is None:
            raise PubmedError("PubMed record is missing Article")

        title = _text(journal_article.find("./ArticleTitle")) or "Untitled"
        abstract_parts: list[str] = []
        for part in journal_article.findall("./Abstract/AbstractText"):
            content = _text(part)
            label = str(part.get("Label") or "").strip()
            if content:
                abstract_parts.append(f"{label}: {content}" if label else content)
        abstract = " ".join(abstract_parts)
        if not abstract:
            raise PubmedError("PubMed record has no abstract")

        authors: list[Author] = []
        for value in journal_article.findall("./AuthorList/Author"):
            name = " ".join(
                part
                for part in (
                    _text(value.find("./ForeName")),
                    _text(value.find("./LastName")),
                )
                if part
            ) or _text(value.find("./CollectiveName"))
            affiliation = _text(value.find("./AffiliationInfo/Affiliation")) or None
            if name:
                authors.append(Author(name=name, affiliation=affiliation))

        publication_date = PubmedClient._publication_date(article)
        timestamp = datetime.combine(
            publication_date,
            datetime_time.min,
            tzinfo=timezone.utc,
        )
        doi = _text(
            article.find("./PubmedData/ArticleIdList/ArticleId[@IdType='doi']")
        ) or None
        pmcid = _text(
            article.find("./PubmedData/ArticleIdList/ArticleId[@IdType='pmc']")
        ) or None
        journal = (
            _text(journal_article.find("./Journal/ISOAbbreviation"))
            or _text(journal_article.find("./Journal/Title"))
            or "PubMed"
        )
        publication_types = tuple(
            value
            for value in (
                _text(item)
                for item in journal_article.findall("./PublicationTypeList/PublicationType")
            )
            if value
        )
        keywords = tuple(
            value
            for value in (
                _text(item)
                for item in citation.findall("./KeywordList/Keyword")
            )
            if value
        )
        original_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        corresponding_institution = next(
            (author.affiliation for author in reversed(authors) if author.affiliation),
            None,
        )
        return ArxivPaper(
            arxiv_id=f"pubmed:{pmid}",
            version=1,
            title=title,
            abstract=abstract,
            authors=tuple(authors),
            categories=("pubmed", *(f"pubmed:{value.lower()}" for value in publication_types)),
            primary_category=f"pubmed:{journal.lower()}",
            published_at=timestamp,
            updated_at=timestamp,
            abstract_url=original_url,
            pdf_url=f"https://doi.org/{doi}" if doi else original_url,
            doi=doi,
            comment=publication_types[0] if publication_types else "journal article",
            query_name="pubmed-ai-title-abstract",
            raw_xml=ET.tostring(article, encoding="unicode"),
            source="pubmed",
            source_metadata={
                "source_external_id": pmid,
                "journal": journal,
                "pmcid": pmcid,
                "publication_types": publication_types,
                "keywords": keywords,
                "corresponding_institution": corresponding_institution,
                "evidence_scope": "abstract_only",
            },
        )

    @staticmethod
    def _publication_date(article: ET.Element) -> date:
        candidates = (
            article.find("./MedlineCitation/Article/ArticleDate"),
            article.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate"),
            article.find("./MedlineCitation/DateCompleted"),
            article.find("./MedlineCitation/DateRevised"),
        )
        for value in candidates:
            if value is None:
                continue
            year_text = _text(value.find("./Year"))
            if not year_text:
                medline = _text(value.find("./MedlineDate"))
                match = re.search(r"\b(19|20)\d{2}\b", medline)
                year_text = match.group(0) if match else ""
            if not year_text:
                continue
            month_text = _text(value.find("./Month")) or "1"
            day_text = _text(value.find("./Day")) or "1"
            month = (
                int(month_text)
                if month_text.isdigit()
                else MONTHS.get(month_text[:3].lower(), 1)
            )
            day_match = re.search(r"\d+", day_text)
            day = int(day_match.group(0)) if day_match else 1
            return date(int(year_text), month, day)
        raise PubmedError("PubMed record is missing a usable publication date")
