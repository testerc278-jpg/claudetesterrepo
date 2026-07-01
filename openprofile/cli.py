"""Command-line interface.

Examples:
  openprofile "Yalumba" --state SA --domain yalumba.com --html out.html
  python -m openprofile "De Bortoli Wines" --domain debortoli.com.au
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config
from .pipeline import Pipeline
from .report import render_html


def _print_summary(profile) -> None:
    e = profile.entity
    t = profile.trading
    line = "=" * 64
    print(line)
    print(f"  OpenProfile  |  query: {profile.query!r}")
    print(line)
    dash = "-"
    print(f"  Entity      : {e.name}")
    print(f"  ABN / status: {e.abn or dash}  /  {e.status or dash}")
    print(f"  Type / state: {e.entity_type or dash}  /  {e.state or dash}")
    print(f"  Domain      : {e.domain or dash}")
    if t:
        print(f"  Trading     : {round(t.score*100)}%  ({t.label})")
    print("  Industry (ANZSIC):")
    if profile.classifications:
        for c in profile.classifications:
            print(f"    - {c.code} {c.label} [{c.sector}]  conf={round(c.confidence*100)}%")
    else:
        print("    - none derived")
    if profile.warnings:
        print("  Caveats:")
        for w in profile.warnings:
            print(f"    ! {w}")
    print(line)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="openprofile",
        description="OSINT business profiler for AU agriculture/horticulture/viticulture.",
    )
    p.add_argument("query", help="Business name to profile")
    p.add_argument("--state", help="Australian state hint, e.g. NSW, VIC, SA")
    p.add_argument("--domain", help="Known website/domain, e.g. example.com.au")
    p.add_argument("--html", metavar="PATH", help="Write an HTML report to PATH")
    p.add_argument("--json", metavar="PATH", help="Write the profile JSON to PATH")
    p.add_argument("--offline", action="store_true",
                   help="Use only cached responses (no network)")
    p.add_argument("--open", action="store_true",
                   help="Open the HTML report in the default browser")
    return p


def main(argv: list[str] | None = None) -> int:
    # Make console output robust on Windows terminals (avoid cp1252 encode errors).
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    args = build_parser().parse_args(argv)
    cfg = Config.from_env()
    if args.offline:
        cfg.offline = True

    profile = Pipeline(cfg).run(args.query, state=args.state, domain=args.domain)
    _print_summary(profile)

    if args.json:
        Path(args.json).write_text(profile.to_json(), encoding="utf-8")
        print(f"  JSON written: {args.json}")
    if args.html:
        out = Path(args.html)
        out.write_text(render_html(profile), encoding="utf-8")
        print(f"  HTML written: {out}")
        if args.open:
            import webbrowser
            webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
