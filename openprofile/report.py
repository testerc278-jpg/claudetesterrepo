"""Render a Profile to a styled, self-contained HTML report (opens in any browser)."""
from __future__ import annotations

import html

from .models import Profile


def _esc(v) -> str:
    return html.escape(str(v)) if v is not None else "&mdash;"


def _confidence_bar(pct: float, color: str) -> str:
    pct = max(0, min(100, round(pct * 100)))
    return (
        f'<div class="bar"><div class="bar-fill" style="width:{pct}%;'
        f'background:{color}"></div></div><span class="pct">{pct}%</span>'
    )


def _trading_color(score: float) -> str:
    if score >= 0.66:
        return "#2e7d32"
    if score >= 0.4:
        return "#f9a825"
    return "#c62828"


def render_html(profile: Profile) -> str:
    e = profile.entity
    t = profile.trading

    # entity facts
    facts = [
        ("Legal name", e.name),
        ("ABN", e.abn),
        ("ACN", e.acn),
        ("Entity type", e.entity_type),
        ("ABR status", e.status),
        ("State", e.state),
        ("Postcode", e.postcode),
        ("Domain", e.domain),
        ("Resolution confidence", f"{round(e.match_score*100)}%" if e.match_score else None),
    ]
    facts_rows = "\n".join(
        f"<tr><th>{_esc(k)}</th><td>{_esc(v)}</td></tr>" for k, v in facts
    )

    # classifications
    if profile.classifications:
        cls_rows = "\n".join(
            f"<tr><td><code>{_esc(c.code)}</code></td><td>{_esc(c.label)}</td>"
            f"<td>{_esc(c.sector)}</td>"
            f"<td>{_confidence_bar(c.confidence, '#1565c0')}</td>"
            f"<td class='terms'>{_esc(', '.join(c.matched_terms))}</td></tr>"
            for c in profile.classifications
        )
        cls_table = (
            "<table><thead><tr><th>ANZSIC</th><th>Class</th><th>Sector</th>"
            "<th>Confidence</th><th>Matched terms</th></tr></thead>"
            f"<tbody>{cls_rows}</tbody></table>"
        )
    else:
        cls_table = "<p class='muted'>No classification derived.</p>"

    # trading signals
    if t:
        sig_rows = "\n".join(
            f"<tr><td>{_esc(s.name)}</td><td>{_esc(s.value)}</td>"
            f"<td class='dir-{_esc(s.direction)}'>{_esc(s.direction)}</td>"
            f"<td>{_esc(round(s.weight, 2))}</td><td>{_esc(s.detail)}</td></tr>"
            for s in t.signals
        )
        trading_block = (
            f"<div class='score' style='color:{_trading_color(t.score)}'>"
            f"{round(t.score*100)}%<span class='score-label'>{_esc(t.label)}</span></div>"
            "<table><thead><tr><th>Signal</th><th>Value</th><th>Direction</th>"
            "<th>Weight</th><th>Detail</th></tr></thead>"
            f"<tbody>{sig_rows}</tbody></table>"
        )
    else:
        trading_block = "<p class='muted'>No trading assessment.</p>"

    # provenance
    prov_rows = "\n".join(
        f"<tr><td>{_esc(p.field_name)}</td><td>{_esc(p.source)}</td>"
        f"<td><a href='{_esc(p.source_url)}'>{_esc(p.source_url)}</a></td>"
        f"<td>{_esc(p.retrieved_at)}</td><td>{_esc(p.note)}</td></tr>"
        for p in profile.provenance
    ) or "<tr><td colspan='5' class='muted'>No provenance recorded.</td></tr>"

    # candidates
    cand_rows = "\n".join(
        f"<tr><td>{_esc(c.name)}</td><td>{_esc(c.abn)}</td><td>{_esc(c.state)}</td>"
        f"<td>{_confidence_bar(c.match_score, '#6a1b9a')}</td></tr>"
        for c in profile.candidates
    ) or "<tr><td colspan='4' class='muted'>No candidates.</td></tr>"

    # warnings
    warn_block = ""
    if profile.warnings:
        items = "".join(f"<li>{_esc(w)}</li>" for w in profile.warnings)
        warn_block = f"<div class='warn'><strong>Caveats</strong><ul>{items}</ul></div>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenProfile &mdash; {_esc(e.name)}</title>
<style>
  :root {{ --ink:#1a1a1a; --muted:#6b7280; --line:#e5e7eb; --bg:#f7f8fa; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         margin:0; background:var(--bg); color:var(--ink); line-height:1.45; }}
  header {{ background:#0f3d2e; color:#eafaf1; padding:28px 40px; }}
  header h1 {{ margin:0; font-size:22px; }}
  header .q {{ opacity:.8; font-size:14px; margin-top:4px; }}
  main {{ max-width:960px; margin:0 auto; padding:28px 40px 60px; }}
  section {{ background:#fff; border:1px solid var(--line); border-radius:10px;
            padding:20px 24px; margin:18px 0; }}
  h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.04em;
       color:var(--muted); margin:0 0 14px; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line);
           vertical-align:top; }}
  table th {{ color:var(--muted); font-weight:600; width:180px; }}
  thead th {{ width:auto; }}
  code {{ background:#eef2ff; padding:1px 6px; border-radius:4px; }}
  .terms {{ color:var(--muted); font-size:12px; }}
  .bar {{ display:inline-block; width:120px; height:8px; background:#eee;
         border-radius:5px; overflow:hidden; vertical-align:middle; }}
  .bar-fill {{ height:100%; }}
  .pct {{ font-size:12px; color:var(--muted); margin-left:8px; }}
  .score {{ font-size:44px; font-weight:700; display:flex; align-items:baseline; gap:14px;
           margin-bottom:12px; }}
  .score-label {{ font-size:16px; font-weight:600; }}
  .dir-positive {{ color:#2e7d32; }} .dir-negative {{ color:#c62828; }}
  .dir-neutral {{ color:var(--muted); }}
  .muted {{ color:var(--muted); }}
  .warn {{ background:#fff8e1; border:1px solid #f0d98a; border-radius:8px;
          padding:12px 16px; margin:18px 0; font-size:13px; }}
  .warn ul {{ margin:8px 0 0 18px; }}
  footer {{ max-width:960px; margin:0 auto; padding:0 40px 40px; color:var(--muted);
           font-size:12px; }}
</style></head>
<body>
<header>
  <h1>OpenProfile &mdash; {_esc(e.name)}</h1>
  <div class="q">Query: &ldquo;{_esc(profile.query)}&rdquo; &middot; generated {_esc(profile.generated_at)}</div>
</header>
<main>
  {warn_block}
  <section><h2>Entity</h2><table>{facts_rows}</table></section>
  <section><h2>Likelihood of currently trading</h2>{trading_block}</section>
  <section><h2>Industry &amp; sector (ANZSIC)</h2>{cls_table}</section>
  <section><h2>Resolution candidates</h2>
    <table><thead><tr><th>Name</th><th>ABN</th><th>State</th><th>Match</th></tr></thead>
    <tbody>{cand_rows}</tbody></table></section>
  <section><h2>Provenance</h2>
    <table><thead><tr><th>Field</th><th>Source</th><th>URL</th><th>Retrieved</th><th>Note</th></tr></thead>
    <tbody>{prov_rows}</tbody></table></section>
</main>
<footer>
  Estimates for analyst review only. Every figure carries a confidence value; low-confidence
  results require human verification. Business-entity data only &mdash; see ETHICS.md.
</footer>
</body></html>"""
