"""Website connector — fetches an entity's own site for activity text + liveness signals.

Pure stdlib HTML-to-text. Extracts: title, meta description, visible body text,
copyright year, and whether the site is reachable (a trading signal).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional

from ..models import ProvenanceRecord
from .base import SourceConnector

_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title: str = ""
        self.meta_description: str = ""
        self._chunks: list[str] = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            a = dict(attrs)
            if a.get("name", "").lower() == "description" and a.get("content"):
                self.meta_description = a["content"].strip()

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip > 0:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title += text
        else:
            self._chunks.append(text)

    @property
    def body_text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._chunks)).strip()


@dataclass
class WebsiteData:
    url: str
    reachable: bool
    title: str = ""
    meta_description: str = ""
    body_text: str = ""
    copyright_year: Optional[int] = None
    error: Optional[str] = None


class WebsiteConnector(SourceConnector):
    name = "website"

    def available(self) -> bool:
        return True

    @staticmethod
    def _guess_url(domain: str) -> str:
        domain = domain.strip()
        if domain.startswith("http://") or domain.startswith("https://"):
            return domain
        return f"https://{domain}"

    @staticmethod
    def _extract_copyright_year(text: str) -> Optional[int]:
        years = re.findall(r"(?:©|\(c\)|copyright)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})",
                           text, flags=re.IGNORECASE)
        if not years:
            return None
        try:
            return max(int(y) for y in years)
        except ValueError:
            return None

    def fetch(self, domain: str) -> tuple[WebsiteData, list[ProvenanceRecord]]:
        url = self._guess_url(domain)
        res = self.client.get(url, check_robots=True)
        if not res.ok:
            return (WebsiteData(url=url, reachable=False, error=res.error or f"HTTP {res.status}"),
                    [ProvenanceRecord("website_reachable", self.name, url,
                                      note=res.error or f"HTTP {res.status}")])
        parser = _TextExtractor()
        try:
            parser.feed(res.text)
        except Exception:  # malformed HTML: keep whatever was parsed
            pass
        body = parser.body_text
        data = WebsiteData(
            url=url,
            reachable=True,
            title=parser.title.strip(),
            meta_description=parser.meta_description,
            body_text=body[:20000],
            copyright_year=self._extract_copyright_year(res.text),
        )
        prov = [ProvenanceRecord("website_reachable", self.name, url, note="200 OK"),
                ProvenanceRecord("activity_text", self.name, url,
                                 note="title+meta+body extracted")]
        return data, prov

    @staticmethod
    def current_year() -> int:
        return datetime.now(timezone.utc).year
