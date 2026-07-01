"""Load the ANZSIC subset taxonomy."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DATA = Path(__file__).parent / "data" / "anzsic_subset.json"


@dataclass(frozen=True)
class AnzsicClass:
    code: str
    label: str
    division: str
    sector: str
    keywords: tuple[str, ...]


@lru_cache(maxsize=1)
def load_taxonomy() -> tuple[AnzsicClass, ...]:
    raw = json.loads(_DATA.read_text(encoding="utf-8"))
    return tuple(
        AnzsicClass(
            code=c["code"],
            label=c["label"],
            division=c["division"],
            sector=c["sector"],
            keywords=tuple(k.lower() for k in c["keywords"]),
        )
        for c in raw["classes"]
    )
