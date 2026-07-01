"""Entity resolution: rank candidate entities; never force a single guess silently."""
from __future__ import annotations

import difflib
import re

from .models import Entity

_LEGAL_SUFFIXES = re.compile(
    r"\b(pty\.?\s*ltd\.?|proprietary|limited|ltd\.?|inc\.?|co\.?|the|and|&)\b",
    re.IGNORECASE,
)


def _normalize_name(name: str) -> str:
    name = _LEGAL_SUFFIXES.sub(" ", name.lower())
    return re.sub(r"[^a-z0-9 ]", " ", name).strip()


def name_similarity(a: str, b: str) -> float:
    na, nb = _normalize_name(a), _normalize_name(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def score_candidate(query: str, cand: Entity, *, state: str | None = None) -> float:
    score = name_similarity(query, cand.name)
    if state and cand.state and state.upper() == cand.state.upper():
        score = min(1.0, score + 0.1)
    if cand.abn:
        score = min(1.0, score + 0.02)  # having a verified ABN is a small corroboration
    return round(score, 3)


def rank_candidates(query: str, candidates: list[Entity], *,
                    state: str | None = None) -> list[Entity]:
    for c in candidates:
        c.match_score = score_candidate(query, c, state=state)
    return sorted(candidates, key=lambda c: c.match_score, reverse=True)


def pick_best(ranked: list[Entity], *, threshold: float = 0.55,
              margin: float = 0.08) -> tuple[Entity | None, bool]:
    """Return (best, confident). 'confident' is False when the top match is weak or
    too close to the runner-up — caller should surface candidates for human review."""
    if not ranked:
        return None, False
    best = ranked[0]
    if best.match_score < threshold:
        return best, False
    if len(ranked) > 1 and (best.match_score - ranked[1].match_score) < margin:
        return best, False
    return best, True
