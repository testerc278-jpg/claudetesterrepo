"""Offline demo generator — builds profiles from SYNTHETIC sample data (no network).

The businesses below are fictional and used only to demonstrate the report + scoring
pipeline for a presentation. Run:  python examples/demo.py
Outputs HTML reports into examples/output/.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openprofile.classifier import IndustryClassifier          # noqa: E402
from openprofile.connectors.rdap import DomainData             # noqa: E402
from openprofile.connectors.website import WebsiteData         # noqa: E402
from openprofile.models import (                               # noqa: E402
    Activity, Entity, Profile, ProvenanceRecord,
)
from openprofile.report import render_html                     # noqa: E402
from openprofile.scoring import score_trading                  # noqa: E402

YEAR = datetime.now(timezone.utc).year

# --- SYNTHETIC sample entities (fictional) ---------------------------------
SAMPLES = [
    {
        "entity": Entity(name="Barossa Ridge Vineyards Pty Ltd", abn="53004085616",
                         entity_type="Australian Private Company", status="Active",
                         state="SA", postcode="5352", domain="barossaridge.example",
                         match_score=0.94),
        "website": WebsiteData(
            url="https://barossaridge.example", reachable=True,
            title="Barossa Ridge Vineyards | Estate Shiraz & Cabernet",
            meta_description=("Family-owned vineyard and winery in the Barossa Valley "
                              "producing estate shiraz, cabernet and grenache. Cellar "
                              "door open daily."),
            body_text=("Our vineyards have grown wine grapes for four generations. "
                       "Winemaker-led cellar door, barrel hall tours, vintage releases."),
            copyright_year=YEAR),
        "domain": DomainData(domain="barossaridge.example", found=True,
                             registered="2004-03-11T00:00:00Z",
                             expires=f"{YEAR+2}-03-11T00:00:00Z",
                             last_changed=f"{YEAR}-01-20T00:00:00Z",
                             statuses=("active",)),
    },
    {
        "entity": Entity(name="Sunraysia Citrus Co", abn="21125863001",
                         entity_type="Sole Trader", status="Active",
                         state="VIC", postcode="3500", domain="sunraysiacitrus.example",
                         match_score=0.88),
        "website": WebsiteData(
            url="https://sunraysiacitrus.example", reachable=True,
            title="Sunraysia Citrus Co — Oranges, Mandarins & Lemons",
            meta_description=("Citrus fruit growers in the Mildura region supplying "
                              "oranges, mandarins and lemons to wholesale markets."),
            body_text="Orchard-fresh citrus, packing shed, export produce, farmgate sales.",
            copyright_year=YEAR - 1),
        "domain": DomainData(domain="sunraysiacitrus.example", found=True,
                             registered="2011-07-02T00:00:00Z",
                             expires=f"{YEAR+1}-07-02T00:00:00Z",
                             last_changed=f"{YEAR-1}-06-15T00:00:00Z",
                             statuses=("active",)),
    },
    {
        "entity": Entity(name="Old Paddock Wool Pty Ltd", abn="99111222333",
                         entity_type="Australian Private Company", status="Cancelled",
                         state="NSW", postcode="2650", domain="oldpaddockwool.example",
                         match_score=0.72),
        "website": WebsiteData(url="https://oldpaddockwool.example", reachable=False,
                               error="Name resolution failed"),
        "domain": DomainData(domain="oldpaddockwool.example", found=True,
                             registered="2007-09-01T00:00:00Z",
                             expires=f"{YEAR-2}-09-01T00:00:00Z",
                             last_changed=f"{YEAR-3}-09-01T00:00:00Z",
                             statuses=("inactive",)),
    },
]


def build_profile(sample: dict) -> Profile:
    clf = IndustryClassifier()
    e: Entity = sample["entity"]
    w: WebsiteData = sample["website"]
    d: DomainData = sample["domain"]

    text_parts = [e.name, e.entity_type or ""]
    if w.reachable:
        text_parts += [w.title, w.meta_description, w.body_text]
    classifications = clf.classify("\n".join(p for p in text_parts if p))

    trading = score_trading(e, w, d)
    activities = []
    if w.reachable and w.meta_description:
        activities.append(Activity(description=w.meta_description, evidence=[w.url]))

    prov = [
        ProvenanceRecord("status", "abn_lookup",
                         f"https://abr.business.gov.au/ABN/View?abn={e.abn}",
                         note=f"AbnStatus={e.status} (SYNTHETIC demo data)"),
        ProvenanceRecord("website_reachable", "website", w.url,
                         note="reachable" if w.reachable else (w.error or "unreachable")),
        ProvenanceRecord("domain_rdap", "rdap", f"https://rdap.org/domain/{d.domain}",
                         note=f"statuses={','.join(d.statuses)}"),
    ]
    return Profile(
        query=e.name, entity=e, classifications=classifications,
        activities=activities, trading=trading, provenance=prov,
        candidates=[e], warnings=["SYNTHETIC demo data — fictional entities."],
    )


def main() -> None:
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)
    index_rows = []
    for s in SAMPLES:
        profile = build_profile(s)
        slug = profile.entity.name.lower().replace(" ", "-").replace(",", "")
        html_path = out_dir / f"{slug}.html"
        html_path.write_text(render_html(profile), encoding="utf-8")
        json_path = out_dir / f"{slug}.json"
        json_path.write_text(profile.to_json(), encoding="utf-8")
        t = profile.trading
        top = profile.classifications[0] if profile.classifications else None
        index_rows.append(
            f"<tr><td><a href='{html_path.name}'>{profile.entity.name}</a></td>"
            f"<td>{round(t.score*100)}% {t.label}</td>"
            f"<td>{(top.code + ' ' + top.label) if top else '—'}</td></tr>"
        )
        print(f"[demo] {profile.entity.name}: trading={round(t.score*100)}% "
              f"({t.label}); top={top.code if top else 'n/a'}")

    index = (
        "<!doctype html><meta charset='utf-8'><title>OpenProfile demo</title>"
        "<style>body{font-family:sans-serif;max-width:760px;margin:40px auto}"
        "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;"
        "padding:8px;text-align:left}</style>"
        "<h1>OpenProfile — demo profiles (synthetic data)</h1>"
        "<table><thead><tr><th>Entity</th><th>Trading</th><th>Top ANZSIC</th></tr></thead>"
        f"<tbody>{''.join(index_rows)}</tbody></table>"
    )
    (out_dir / "index.html").write_text(index, encoding="utf-8")
    print(f"\n[demo] Open: {(out_dir / 'index.html').resolve()}")


if __name__ == "__main__":
    main()
