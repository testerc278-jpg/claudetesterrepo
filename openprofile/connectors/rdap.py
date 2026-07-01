"""RDAP connector — domain registration metadata as a trading/liveness signal.

Uses the rdap.org bootstrap proxy. Many ccTLDs (including .au) restrict RDAP data;
this connector degrades gracefully when fields are unavailable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..models import ProvenanceRecord
from .base import SourceConnector

_BOOTSTRAP = "https://rdap.org/domain/"


@dataclass
class DomainData:
    domain: str
    found: bool
    registered: Optional[str] = None
    expires: Optional[str] = None
    last_changed: Optional[str] = None
    statuses: tuple[str, ...] = ()
    error: Optional[str] = None


def _registrable(domain: str) -> str:
    d = domain.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d.split("/")[0]


def _events(obj: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for ev in obj.get("events", []) or []:
        action = ev.get("eventAction")
        date = ev.get("eventDate")
        if action and date:
            out[action] = date
    return out


class RdapConnector(SourceConnector):
    name = "rdap"

    def available(self) -> bool:
        return True

    def fetch(self, domain: str) -> tuple[DomainData, list[ProvenanceRecord]]:
        d = _registrable(domain)
        url = f"{_BOOTSTRAP}{d}"
        res = self.client.get(url, check_robots=False)
        if not res.ok:
            return (DomainData(d, found=False, error=res.error or f"HTTP {res.status}"),
                    [ProvenanceRecord("domain_rdap", self.name, url,
                                      note=res.error or f"HTTP {res.status}")])
        try:
            obj = json.loads(res.text)
        except json.JSONDecodeError:
            return (DomainData(d, found=False, error="invalid RDAP JSON"),
                    [ProvenanceRecord("domain_rdap", self.name, url, note="invalid JSON")])
        ev = _events(obj)
        data = DomainData(
            domain=d,
            found=True,
            registered=ev.get("registration"),
            expires=ev.get("expiration"),
            last_changed=ev.get("last changed") or ev.get("last update of RDAP database"),
            statuses=tuple(obj.get("status", []) or ()),
        )
        return data, [ProvenanceRecord("domain_rdap", self.name, url,
                                       note=f"statuses={','.join(data.statuses) or 'n/a'}")]

    @staticmethod
    def parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
