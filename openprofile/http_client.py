"""Polite HTTP client: rate limiting, robots.txt, on-disk caching, provenance-friendly.

Stdlib only (urllib). Returns (status, text, from_cache).
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import Config


@dataclass
class FetchResult:
    url: str
    status: int
    text: str
    from_cache: bool
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300


class PoliteClient:
    def __init__(self, config: Config):
        self.cfg = config
        self.cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    # -- caching -----------------------------------------------------------
    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self.cfg.cache_dir / f"{digest}.json"

    def _read_cache(self, url: str) -> Optional[FetchResult]:
        p = self._cache_path(url)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return FetchResult(url, data["status"], data["text"], from_cache=True)
        except (OSError, json.JSONDecodeError, KeyError):
            return None

    def _write_cache(self, res: FetchResult) -> None:
        if not res.ok:
            return
        try:
            self._cache_path(res.url).write_text(
                json.dumps({"status": res.status, "text": res.text}),
                encoding="utf-8",
            )
        except OSError:
            pass

    # -- politeness --------------------------------------------------------
    def _throttle(self, host: str) -> None:
        last = self._last_request.get(host, 0.0)
        wait = self.cfg.min_request_interval - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_request[host] = time.time()

    def _robots_ok(self, url: str) -> bool:
        parts = urllib.parse.urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        rp = self._robots.get(host)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{host}/robots.txt")
            try:
                rp.read()
            except Exception:
                # If robots can't be read, be conservative-but-functional: allow.
                rp = None
            self._robots[host] = rp  # type: ignore[assignment]
        if rp is None:
            return True
        return rp.can_fetch(self.cfg.user_agent, url)

    # -- public API --------------------------------------------------------
    def get(self, url: str, *, check_robots: bool = True) -> FetchResult:
        cached = self._read_cache(url)
        if cached is not None:
            return cached
        if self.cfg.offline:
            return FetchResult(url, 0, "", from_cache=False, error="offline: no cached copy")

        if check_robots and not self._robots_ok(url):
            return FetchResult(url, 0, "", from_cache=False, error="blocked by robots.txt")

        parts = urllib.parse.urlsplit(url)
        self._throttle(parts.netloc)
        req = urllib.request.Request(url, headers={"User-Agent": self.cfg.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.request_timeout) as resp:
                raw = resp.read()
                charset = resp.headers.get_content_charset() or "utf-8"
                text = raw.decode(charset, errors="replace")
                res = FetchResult(url, resp.status, text, from_cache=False)
                self._write_cache(res)
                return res
        except urllib.error.HTTPError as e:
            return FetchResult(url, e.code, "", from_cache=False, error=f"HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return FetchResult(url, 0, "", from_cache=False, error=str(e))
