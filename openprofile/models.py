"""Canonical data contracts. Everything else conforms to these.

Pure-stdlib dataclasses so the tool runs on a bare Python install.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProvenanceRecord:
    """Where a single datum came from. No data point without one of these."""
    field_name: str
    source: str            # connector name, e.g. "abn_lookup"
    source_url: str
    retrieved_at: str = field(default_factory=_now_iso)
    note: str = ""


@dataclass
class Entity:
    """A resolved (or candidate) legal entity."""
    name: str
    jurisdiction: str = "AU"
    abn: Optional[str] = None
    acn: Optional[str] = None
    entity_type: Optional[str] = None
    status: Optional[str] = None          # e.g. "Active", "Cancelled" (from ABR)
    state: Optional[str] = None           # e.g. "NSW", "VIC"
    postcode: Optional[str] = None
    domain: Optional[str] = None
    match_score: float = 0.0              # 0..1 resolution confidence


@dataclass
class ClassificationResult:
    """Industry/sector classification against a taxonomy (ANZSIC)."""
    code: str
    label: str
    division: str                         # ANZSIC division letter, e.g. "A"
    sector: str                           # human sector, e.g. "Agriculture"
    confidence: float                     # 0..1
    matched_terms: list[str] = field(default_factory=list)


@dataclass
class TradingSignal:
    """One piece of evidence bearing on 'is this entity currently trading?'"""
    name: str
    value: Any
    weight: float                         # contribution magnitude
    direction: str                        # "positive" | "negative" | "neutral"
    detail: str = ""


@dataclass
class TradingLikelihood:
    score: float                          # 0..1 calibrated-ish
    label: str                            # "Likely trading" / "Uncertain" / "Likely not trading"
    signals: list[TradingSignal] = field(default_factory=list)
    as_of: str = field(default_factory=_now_iso)


@dataclass
class Activity:
    description: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class Profile:
    """The complete output object."""
    query: str
    entity: Entity
    classifications: list[ClassificationResult] = field(default_factory=list)
    activities: list[Activity] = field(default_factory=list)
    trading: Optional[TradingLikelihood] = None
    provenance: list[ProvenanceRecord] = field(default_factory=list)
    candidates: list[Entity] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
