"""ABN Lookup connector — Australian Business Register (official web service).

The ABR JSON web services require a free registered AuthenticationGuid, supplied via the
ABN_LOOKUP_GUID environment variable. Without it this connector is unavailable and the
pipeline degrades gracefully to web/RDAP signals only.

Endpoints (JSON variants return a JSONP `callback(...)` wrapper which we strip):
  - MatchingNames.aspx  -> name search returning candidate ABNs
  - AbnDetails.aspx      -> full detail for one ABN

Ref: https://abr.business.gov.au/Tools/WebServices  (verify terms before production use)
"""
from __future__ import annotations

import json
import re
import urllib.parse
from typing import Optional

from ..models import Entity, ProvenanceRecord
from .base import SourceConnector

_BASE = "https://abr.business.gov.au/json"
_JSONP_RE = re.compile(r"^[^(]*\((.*)\)[^)]*$", re.DOTALL)


def _parse_jsonp(text: str) -> Optional[dict]:
    text = text.strip()
    if not text:
        return None
    m = _JSONP_RE.match(text)
    payload = m.group(1) if m else text
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


class AbnLookupConnector(SourceConnector):
    name = "abn_lookup"

    def available(self) -> bool:
        return bool(self.cfg.abn_lookup_guid)

    def _detail_url(self, abn: str) -> str:
        q = urllib.parse.urlencode({"abn": abn, "guid": self.cfg.abn_lookup_guid})
        return f"{_BASE}/AbnDetails.aspx?{q}"

    def search(self, name: str) -> tuple[list[Entity], list[ProvenanceRecord]]:
        """Return candidate entities from an ABR name search."""
        if not self.available():
            return [], []
        q = urllib.parse.urlencode(
            {"name": name, "maxResults": self.cfg.max_candidates,
             "guid": self.cfg.abn_lookup_guid}
        )
        url = f"{_BASE}/MatchingNames.aspx?{q}"
        res = self.client.get(url, check_robots=False)  # official API, not crawled pages
        if not res.ok:
            return [], []
        data = _parse_jsonp(res.text) or {}
        names = data.get("Names", []) or []
        candidates: list[Entity] = []
        prov: list[ProvenanceRecord] = []
        for item in names:
            abn = (item.get("Abn") or "").replace(" ", "")
            ent = Entity(
                name=item.get("Name", "").strip(),
                abn=abn or None,
                state=item.get("State") or None,
                postcode=item.get("Postcode") or None,
                jurisdiction="AU",
            )
            candidates.append(ent)
        if candidates:
            prov.append(ProvenanceRecord(
                field_name="candidates", source=self.name, source_url=url,
                note=f"{len(candidates)} name matches",
            ))
        return candidates, prov

    def detail(self, abn: str) -> tuple[Optional[Entity], list[ProvenanceRecord]]:
        """Enrich a single ABN with full ABR detail (status, type, name)."""
        if not self.available() or not abn:
            return None, []
        url = self._detail_url(abn)
        res = self.client.get(url, check_robots=False)
        if not res.ok:
            return None, []
        data = _parse_jsonp(res.text) or {}
        if not data or data.get("Abn") in (None, ""):
            return None, []
        business_names = data.get("BusinessName") or []
        if isinstance(business_names, str):
            business_names = [business_names]
        ent = Entity(
            name=data.get("EntityName") or (business_names[0] if business_names else ""),
            abn=(data.get("Abn") or "").replace(" ", "") or None,
            acn=(data.get("Acn") or "").replace(" ", "") or None,
            entity_type=data.get("EntityTypeName") or None,
            status=data.get("AbnStatus") or None,
            state=data.get("AddressState") or None,
            postcode=data.get("AddressPostcode") or None,
            jurisdiction="AU",
        )
        prov = [
            ProvenanceRecord(field_name="status", source=self.name, source_url=url,
                             note=f"AbnStatus={ent.status}"),
            ProvenanceRecord(field_name="entity_type", source=self.name, source_url=url),
        ]
        return ent, prov
