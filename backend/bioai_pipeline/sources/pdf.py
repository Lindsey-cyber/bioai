from __future__ import annotations

import re
import time
import urllib.error
import urllib.request

import pymupdf

from bioai_pipeline.sources.arxiv import USER_AGENT


class PdfError(RuntimeError):
    pass


class PdfTextClient:
    def __init__(self, max_bytes: int = 25_000_000):
        self.max_bytes = max_bytes

    def fetch_text(
        self,
        url: str,
        max_chars: int,
        max_pages: int | None = None,
    ) -> str:
        payload = self._get(url)
        try:
            document = pymupdf.open(stream=payload, filetype="pdf")
        except Exception as exc:
            raise PdfError(f"Could not open arXiv PDF: {exc}") from exc

        parts: list[str] = []
        size = 0
        try:
            for page_number, page in enumerate(document):
                if max_pages is not None and page_number >= max_pages:
                    break
                text = page.get_text("text")
                if not text:
                    continue
                remaining = max_chars - size
                if remaining <= 0:
                    break
                parts.append(text[:remaining])
                size += min(len(text), remaining)
        finally:
            document.close()
        combined = "\n".join(parts)
        return re.sub(r"[ \t]+", " ", combined).strip()

    def _get(self, url: str) -> bytes:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/pdf"},
        )
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    length = response.headers.get("Content-Length")
                    if length and int(length) > self.max_bytes:
                        raise PdfError(f"PDF exceeds {self.max_bytes} bytes")
                    payload = response.read(self.max_bytes + 1)
                    if len(payload) > self.max_bytes:
                        raise PdfError(f"PDF exceeds {self.max_bytes} bytes")
                    return payload
            except PdfError:
                raise
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if isinstance(exc, urllib.error.HTTPError) and exc.code < 500 and exc.code != 429:
                    break
                if attempt < 3:
                    time.sleep(2**attempt)
        raise PdfError(f"arXiv PDF request failed after retries: {last_error}")
