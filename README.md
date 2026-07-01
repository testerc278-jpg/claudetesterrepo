# OpenProfile

An open-source **OSINT business-profiling** proof of concept, focused on **Australian
agriculture, horticulture and viticulture** entities. Given a business name, it estimates:

- **Business activities** — extracted from the entity's public web presence.
- **Sector & industry** — classified against an **ANZSIC** taxonomy subset.
- **Likelihood of currently trading** — a transparent, weighted-evidence 0–1 score.

Every field carries **provenance** (source + timestamp) and every inference carries a
**confidence** value. Business-entity data only — see [`ETHICS.md`](ETHICS.md).

> Proof of concept. Zero third-party dependencies — runs on a bare Python ≥3.10 install.

## Quick start

```bash
# 1) Offline demo with synthetic sample businesses (no network, guaranteed to work)
python examples/demo.py
#    -> open examples/output/index.html

# 2) Live single profile (website + domain RDAP signals)
python -m openprofile "Barossa Ridge Vineyards" --domain example.com.au --html report.html --open

# 3) With the Australian Business Register enabled (recommended)
#    Register for a free ABN Lookup GUID, then:
setx ABN_LOOKUP_GUID "your-guid-here"      # Windows (new shell picks it up)
export ABN_LOOKUP_GUID="your-guid-here"    # macOS/Linux
python -m openprofile "De Bortoli Wines" --state NSW --domain debortoli.com.au --html report.html
```

Run the tests:

```bash
python -m pip install pytest
python -m pytest -q
```

## How it works (pipeline)

```
resolve (ABR name search + fuzzy ranking)
  -> enrich (ABR ABN detail: status, type)
  -> fetch  (website text + liveness, domain RDAP)
  -> classify (ANZSIC lexical classifier)
  -> score (weighted-evidence trading likelihood)
  -> assemble Profile -> CLI summary + HTML/JSON report
```

## Data sources

| Source | Connector | Signal | Notes |
|---|---|---|---|
| Australian Business Register (ABN Lookup) | `abn_lookup` | Legal name, ABN status, entity type | Requires free `ABN_LOOKUP_GUID`. Official API. |
| Entity website | `website` | Activity text, liveness, copyright year | Honours `robots.txt`; rate-limited. |
| Domain RDAP | `rdap` | Registration/expiry/last-change | ccTLD (.au) fields may be restricted. |

**Grounding note:** connector behaviour, endpoints and terms are *[training knowledge —
uncertain]* and must be verified against each source's current API and Terms of Service
before production use. The ANZSIC codes bundled here are illustrative and should be
validated against the official ABS reference (cat. 1292.0).

## Guardrails (enforced in code)

- Public data only; `robots.txt` respected; polite rate limiting; descriptive User-Agent.
- Provenance recorded for every datum; confidence attached to every inference.
- Low-confidence entity resolution surfaces a candidate list instead of guessing.
- No profiling of the individuals behind an entity.

## Project layout

```
openprofile/
  models.py        # dataclass contracts (Entity, Classification, Signals, Profile, Provenance)
  config.py        # env-driven config
  http_client.py   # polite fetch: robots.txt, throttling, on-disk cache
  taxonomy.py      # ANZSIC subset loader
  classifier.py    # IDF-weighted lexical industry classifier (offline, deterministic)
  resolver.py      # fuzzy entity resolution + candidate ranking
  scoring.py       # transparent trading-likelihood model
  pipeline.py      # orchestrator
  report.py        # self-contained HTML report
  cli.py           # command-line interface
  connectors/      # abn_lookup, website, rdap
  data/anzsic_subset.json
examples/demo.py   # offline synthetic demo
tests/             # pytest suite
```

## Known limitations / next steps

- Entity resolution is name-fuzzy; add address/domain corroboration and an accept/review UI.
- Classifier is lexical; an embedding + LLM-reconciler upgrade path is designed but not required.
- Trading score weights are hand-set; calibrate against a labelled active/dissolved dataset.
- Add connectors: OpenCorporates, ASIC, GLEIF (LEI), OpenStreetMap POIs.
