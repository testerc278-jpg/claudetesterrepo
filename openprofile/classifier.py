"""Lexical industry classifier (no API key, fully offline, deterministic).

Approach: IDF-weighted keyword/phrase matching against the ANZSIC subset, with a
saturation factor so confidence reflects *how much* evidence was found, not just which
class won. This is the explainable, auditable baseline described in the design brief;
an embedding/LLM reconciler is a documented upgrade path, not required for the POC.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .models import ClassificationResult
from .taxonomy import AnzsicClass, load_taxonomy

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def _normalize(text: str) -> str:
    return " " + " ".join(_TOKEN_RE.findall(text.lower())) + " "


def _keyword_idf() -> dict[str, float]:
    classes = load_taxonomy()
    n = len(classes)
    df: Counter[str] = Counter()
    for c in classes:
        for kw in set(c.keywords):
            df[kw] += 1
    return {kw: math.log((1 + n) / (1 + d)) + 1.0 for kw, d in df.items()}


class IndustryClassifier:
    SATURATION_K = 3.0  # evidence needed before confidence can approach its share

    def __init__(self):
        self.idf = _keyword_idf()

    def _score_class(self, doc: str, c: AnzsicClass) -> tuple[float, list[str]]:
        score = 0.0
        matched: list[str] = []
        for kw in c.keywords:
            needle = f" {kw} " if " " not in kw else kw
            count = doc.count(needle) if " " not in kw else doc.count(f" {kw} ") + doc.count(f" {kw}")
            if count <= 0:
                continue
            phrase_bonus = 1.0 + 0.5 * (kw.count(" "))
            weight = self.idf.get(kw, 1.0)
            score += weight * phrase_bonus * (1.0 + math.log(count))
            matched.append(kw)
        return score, matched

    def classify(self, text: str, top_k: int = 3) -> list[ClassificationResult]:
        if not text or not text.strip():
            return []
        doc = _normalize(text)
        scored = []
        total_matches = 0
        for c in load_taxonomy():
            s, matched = self._score_class(doc, c)
            if s > 0:
                scored.append((s, matched, c))
                total_matches += len(matched)
        if not scored:
            return []

        total_score = sum(s for s, _, _ in scored)
        saturation = total_matches / (total_matches + self.SATURATION_K)
        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[ClassificationResult] = []
        for s, matched, c in scored[:top_k]:
            share = s / total_score
            confidence = round(min(0.99, share * saturation + 0.01), 3)
            results.append(ClassificationResult(
                code=c.code, label=c.label, division=c.division, sector=c.sector,
                confidence=confidence, matched_terms=sorted(set(matched)),
            ))
        return results
