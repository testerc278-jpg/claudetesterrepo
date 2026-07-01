"""Runtime configuration. Loaded from environment with safe defaults."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    abn_lookup_guid: str | None = None
    user_agent: str = (
        "OpenProfile/0.1 (+https://github.com/openprofile; OSINT business research; "
        "respects robots.txt)"
    )
    request_timeout: float = 15.0
    min_request_interval: float = 1.0     # seconds between requests to the same host
    cache_dir: Path = Path(".openprofile_cache")
    offline: bool = False                 # if True, only use cached responses
    max_candidates: int = 8

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            abn_lookup_guid=os.environ.get("ABN_LOOKUP_GUID") or None,
            offline=os.environ.get("OPENPROFILE_OFFLINE", "").lower() in ("1", "true", "yes"),
        )
