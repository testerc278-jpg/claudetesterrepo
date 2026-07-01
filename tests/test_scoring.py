from openprofile.connectors.rdap import DomainData
from openprofile.connectors.website import WebsiteConnector, WebsiteData
from openprofile.models import Entity
from openprofile.scoring import score_trading


def test_active_abr_and_live_site_is_likely_trading():
    year = WebsiteConnector.current_year()
    entity = Entity(name="Acme Vines Pty Ltd", abn="12345678901", status="Active")
    website = WebsiteData(url="https://acme.example", reachable=True, copyright_year=year)
    domain = DomainData(domain="acme.example", found=True,
                        expires="2030-01-01T00:00:00Z")
    result = score_trading(entity, website, domain)
    assert result.score >= 0.66
    assert result.label == "Likely trading"


def test_cancelled_abn_and_dead_site_is_unlikely():
    entity = Entity(name="Defunct Farm Pty Ltd", status="Cancelled")
    website = WebsiteData(url="https://defunct.example", reachable=False, error="timeout")
    result = score_trading(entity, website, None)
    assert result.score < 0.4
    assert result.label == "Likely not trading"


def test_no_signals_stays_near_neutral():
    result = score_trading(None, None, None)
    assert 0.35 <= result.score <= 0.65


def test_signals_are_explained():
    entity = Entity(name="X", status="Active")
    result = score_trading(entity, None, None)
    assert any(s.name == "abr_status" and s.direction == "positive" for s in result.signals)
