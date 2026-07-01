"""ABR connector tests against RECORDED fixtures (never hits the live service).

The fixtures under tests/fixtures/*.jsonp mimic the ABN Lookup JSON web-service shape
(a `callback(...)` JSONP wrapper). Field names are illustrative and should be validated
against the official ABR schema when a real AuthenticationGuid is available.
"""
from __future__ import annotations

from pathlib import Path

from openprofile.config import Config
from openprofile.connectors.abn_lookup import AbnLookupConnector
from openprofile.http_client import FetchResult

FIX = Path(__file__).parent / "fixtures"


class FakeClient:
    """Routes ABR endpoints to recorded fixtures; asserts no other URL is called."""

    def __init__(self):
        self.calls: list[str] = []

    def get(self, url: str, *, check_robots: bool = True) -> FetchResult:
        self.calls.append(url)
        if "MatchingNames" in url:
            text = (FIX / "abr_matchingnames.jsonp").read_text(encoding="utf-8")
        elif "AbnDetails" in url:
            text = (FIX / "abr_abndetails.jsonp").read_text(encoding="utf-8")
        else:
            raise AssertionError(f"unexpected live URL in test: {url}")
        return FetchResult(url, 200, text, from_cache=True)


def _connector() -> AbnLookupConnector:
    cfg = Config(abn_lookup_guid="00000000-0000-0000-0000-000000000000")  # dummy, not real
    c = AbnLookupConnector.__new__(AbnLookupConnector)
    c.client = FakeClient()
    c.cfg = cfg
    return c


def test_available_requires_guid():
    with_guid = _connector()
    assert with_guid.available() is True
    no_guid = AbnLookupConnector.__new__(AbnLookupConnector)
    no_guid.cfg = Config(abn_lookup_guid=None)
    assert no_guid.available() is False


def test_search_parses_jsonp_candidates():
    c = _connector()
    candidates, prov = c.search("Barossa Ridge")
    assert len(candidates) == 2
    top = candidates[0]
    assert top.name == "BAROSSA RIDGE VINEYARDS PTY LTD"
    assert top.abn == "53004085616"          # spaces stripped
    assert top.state == "SA"
    assert prov and prov[0].source == "abn_lookup"


def test_detail_enriches_status_and_type():
    c = _connector()
    entity, prov = c.detail("53004085616")
    assert entity is not None
    assert entity.status == "Active"
    assert entity.entity_type == "Australian Private Company"
    assert entity.acn == "004085616"
    assert entity.state == "SA"
    assert any(p.field_name == "status" for p in prov)


def test_no_guid_short_circuits_without_network():
    no_guid = AbnLookupConnector.__new__(AbnLookupConnector)
    no_guid.cfg = Config(abn_lookup_guid=None)
    no_guid.client = FakeClient()
    assert no_guid.search("anything") == ([], [])
    assert no_guid.client.calls == []        # never touched the network
