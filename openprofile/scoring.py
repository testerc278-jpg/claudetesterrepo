"""Trading-likelihood scoring: transparent weighted-evidence model.

Each signal contributes a signed, weighted log-odds nudge to a neutral prior. The total
is squashed with a logistic to a 0..1 score. Weights are explicit and config-driven so the
result is fully explainable (per the design brief). Calibration against labelled
active/dissolved entities is a documented follow-up.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional

from .connectors.rdap import DomainData, RdapConnector
from .connectors.website import WebsiteData
from .models import Entity, TradingLikelihood, TradingSignal

# log-odds weights (positive => more likely trading)
W = {
    "abr_active": 2.2,
    "abr_cancelled": -3.0,
    "abr_unknown_status": -0.2,
    "website_reachable": 1.1,
    "website_unreachable": -0.8,
    "copyright_current": 0.9,
    "copyright_recent": 0.3,
    "copyright_stale": -0.7,
    "domain_active": 0.6,
    "domain_expired": -1.5,
    "domain_recent_change": 0.4,
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _label(score: float) -> str:
    if score >= 0.66:
        return "Likely trading"
    if score >= 0.4:
        return "Uncertain"
    return "Likely not trading"


def score_trading(
    entity: Optional[Entity],
    website: Optional[WebsiteData],
    domain: Optional[DomainData],
) -> TradingLikelihood:
    signals: list[TradingSignal] = []
    logit = 0.0
    now = datetime.now(timezone.utc)
    year = now.year

    # --- ABR status (strongest signal) ---
    if entity and entity.status:
        st = entity.status.lower()
        if "active" in st:
            logit += W["abr_active"]
            signals.append(TradingSignal("abr_status", entity.status, W["abr_active"],
                                         "positive", "Registered as Active on the ABR"))
        elif "cancel" in st:
            logit += W["abr_cancelled"]
            signals.append(TradingSignal("abr_status", entity.status, W["abr_cancelled"],
                                         "negative", "ABN cancelled on the ABR"))
        else:
            logit += W["abr_unknown_status"]
            signals.append(TradingSignal("abr_status", entity.status,
                                         W["abr_unknown_status"], "neutral",
                                         "ABR status present but unrecognised"))
    else:
        signals.append(TradingSignal("abr_status", None, 0.0, "neutral",
                                     "No ABR status (no GUID configured or not found)"))

    # --- website liveness ---
    if website is not None:
        if website.reachable:
            logit += W["website_reachable"]
            signals.append(TradingSignal("website_reachable", True, W["website_reachable"],
                                         "positive", f"Website responded: {website.url}"))
            cy = website.copyright_year
            if cy:
                if cy >= year:
                    logit += W["copyright_current"]
                    signals.append(TradingSignal("copyright_year", cy, W["copyright_current"],
                                                 "positive", "Copyright is current year"))
                elif cy >= year - 1:
                    logit += W["copyright_recent"]
                    signals.append(TradingSignal("copyright_year", cy, W["copyright_recent"],
                                                 "positive", "Copyright within last year"))
                else:
                    logit += W["copyright_stale"]
                    signals.append(TradingSignal("copyright_year", cy, W["copyright_stale"],
                                                 "negative", f"Copyright year is stale ({cy})"))
        else:
            logit += W["website_unreachable"]
            signals.append(TradingSignal("website_reachable", False, W["website_unreachable"],
                                         "negative", website.error or "Website unreachable"))

    # --- domain registration (RDAP) ---
    if domain is not None and domain.found:
        exp = RdapConnector.parse_dt(domain.expires)
        if exp is not None and exp < now:
            logit += W["domain_expired"]
            signals.append(TradingSignal("domain_expiry", domain.expires, W["domain_expired"],
                                         "negative", "Domain registration expired"))
        else:
            logit += W["domain_active"]
            signals.append(TradingSignal("domain_expiry", domain.expires or "unknown",
                                         W["domain_active"], "positive",
                                         "Domain registration not expired"))
        changed = RdapConnector.parse_dt(domain.last_changed)
        if changed is not None and (now - changed).days <= 365:
            logit += W["domain_recent_change"]
            signals.append(TradingSignal("domain_last_changed", domain.last_changed,
                                         W["domain_recent_change"], "positive",
                                         "Domain record changed within last year"))

    score = round(_sigmoid(logit), 3)
    return TradingLikelihood(score=score, label=_label(score), signals=signals)
