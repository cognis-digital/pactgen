"""Command-line interface for PACTGEN.

Examples
--------
  # Render a proposal spec to HTML
  python -m pactgen build demos/01-basic/proposal.yaml -o proposal.html

  # Just validate the line-item math (CI gate: exits non-zero on mismatch)
  python -m pactgen build demos/01-basic/proposal.yaml --check

  # Machine-readable output for piping / CI
  python -m pactgen build demos/01-basic/proposal.yaml --format json
"""

from __future__ import annotations

import argparse
import json
import sys

from . import TOOL_NAME, TOOL_VERSION
from .core import (
    parse_proposal_file,
    render_html,
    proposal_to_dict,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Generate proposals/SOWs from a YAML scope + pricing table to HTML, "
        "with line-item math checks.",
        epilog="Example: python -m pactgen build proposal.yaml -o out.html",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {TOOL_VERSION}")
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format for the summary/report (default: table).",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    build = sub.add_parser(
        "build",
        help="Parse a proposal spec, validate the math, and render HTML.",
        description="Parse a YAML proposal spec, validate line-item math, and "
        "optionally write an HTML document.",
    )
    build.add_argument("spec", help="Path to the YAML proposal spec.")
    build.add_argument("-o", "--out", help="Write rendered HTML to this path.")
    build.add_argument(
        "--check",
        action="store_true",
        help="Only validate math; do not render HTML. Exits non-zero on any issue.",
    )
    return parser


def _print_table(report: dict, html_out: str | None) -> None:
    t = report["totals"]
    cur = report["currency"]
    print(f"{report['title']}  ({report['vendor']} -> {report['client']}, {report['date']})")
    print("-" * 60)
    print(f"{'Item':32}{'Qty':>6}{'Unit':>10}{'Total':>12}")
    for it in report["items"]:
        name = it["name"][:30]
        print(f"{name:32}{it['qty']:>6g}{it['unit_price']:>10.2f}{it['total']:>12.2f}")
    print("-" * 60)
    print(f"{'Subtotal':>48}{t['subtotal']:>12.2f}")
    if report["discount_pct"]:
        print(f"{'Discount':>48}{-t['discount']:>12.2f}")
    if report["tax_pct"]:
        print(f"{'Tax':>48}{t['tax']:>12.2f}")
    print(f"{'TOTAL (' + cur + ')':>48}{t['grand_total']:>12.2f}")
    print()
    if report["issues"]:
        print(f"MATH CHECK FAILED ({len(report['issues'])} issue(s)):")
        for iss in report["issues"]:
            print(f"  - {iss['where']}: {iss['message']} "
                  f"(expected {iss['expected']:.2f}, found {iss['found']:.2f})")
    else:
        print("Math check: OK")
    if html_out:
        print(f"HTML written to {html_out}")


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "build":
        parser.print_help()
        return 0

    try:
        proposal = parse_proposal_file(args.spec)
    except FileNotFoundError:
        print(f"error: spec not found: {args.spec}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = proposal_to_dict(proposal)
    html_out = None

    if not args.check and args.out:
        html_doc = render_html(proposal)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(html_doc)
        html_out = args.out

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        _print_table(report, html_out)
        if not args.check and not args.out:
            # Convenience: emit HTML to stdout if no destination and not check-only.
            pass

    # CI gate: any math issue is a failure.
    return 1 if report["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
