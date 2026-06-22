"""Tests for the CSV exporter, --format positioning, version sourcing, and demos."""

import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pactgen import TOOL_VERSION  # noqa: E402
from pactgen.core import (  # noqa: E402
    parse_proposal,
    parse_proposal_file,
    compute_totals,
    check_math,
    render_csv,
)
from pactgen.cli import main  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS = os.path.join(ROOT, "demos")


def _demo(*parts):
    return os.path.join(DEMOS, *parts)


# --------------------------------------------------------------------------- #
# Version is sourced from the VERSION file, not the 0.1.0 fallback.
# --------------------------------------------------------------------------- #

def test_version_matches_version_file():
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as fh:
        expected = fh.read().strip()
    assert TOOL_VERSION == expected


# --------------------------------------------------------------------------- #
# CSV exporter
# --------------------------------------------------------------------------- #

CLEAN = """\
title: T
vendor: V
client: C
currency: USD
items:
  - name: Work
    description: stuff
    qty: 3
    unit_price: 100
    total: 300
pricing:
  discount_pct: 10
  tax_pct: 5
"""


def test_render_csv_roundtrips_and_sums():
    p = parse_proposal(CLEAN)
    text = render_csv(p)
    rows = list(csv.DictReader(io.StringIO(text)))
    items = [r for r in rows if r["section"] == "item"]
    summary = {r["name"]: r["total"] for r in rows if r["section"] == "summary"}
    assert len(items) == 1
    assert items[0]["total"] == "300.00"
    # subtotal 300, -10% = 270, +5% tax = 283.50
    assert summary["Subtotal"] == "300.00"
    assert summary["Grand Total"] == "283.50"


def test_render_csv_quotes_commas():
    spec = CLEAN.replace("description: stuff", "description: a, b, c")
    p = parse_proposal(spec)
    text = render_csv(p)
    # The comma-bearing field must be quoted so the CSV stays well-formed.
    assert '"a, b, c"' in text
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[1][2] == "a, b, c"


def test_cli_csv_to_stdout(capsys):
    rc = main(["build", _demo("08-csv-export", "proposal.yaml"), "--format", "csv"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("section,name,description")
    assert "Grand Total" in out
    assert "22999.68" in out


def test_cli_csv_to_file(tmp_path):
    out = tmp_path / "bom.csv"
    rc = main(["build", _demo("08-csv-export", "proposal.yaml"), "--format", "csv", "-o", str(out)])
    assert rc == 0
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("section,")


# --------------------------------------------------------------------------- #
# --format works both before and after the subcommand
# --------------------------------------------------------------------------- #

def test_format_after_subcommand(capsys):
    rc = main(["build", _demo("04-discount-rounding", "proposal.yaml"), "--format", "json"])
    assert rc == 0
    assert capsys.readouterr().out.lstrip().startswith("{")


def test_format_before_subcommand(capsys):
    rc = main(["--format", "json", "build", _demo("04-discount-rounding", "proposal.yaml")])
    assert rc == 0
    assert capsys.readouterr().out.lstrip().startswith("{")


# --------------------------------------------------------------------------- #
# Every demo behaves exactly as its SCENARIO.md documents.
# --------------------------------------------------------------------------- #

PASSING = [
    ("02-clean-saas-retainer", "proposal.yaml", 11685.00),
    ("03-eur-fixed-bid", "proposal.yaml", 20825.00),
    ("04-discount-rounding", "proposal.yaml", 3538.63),
    ("06-field-aliases", "proposal.yaml", 1956.00),
    ("08-csv-export", "proposal.yaml", 22999.68),
]

FAILING = [
    ("01-basic", ("proposal.yaml",)),
    ("05-sow-line-error", ("proposal.yaml",)),
    ("07-invalid-inputs", ("proposal.yaml",)),
    ("09-ci-batch", ("proposals", "brightline-expansion.yaml")),
]


def test_passing_demos_reconcile():
    for folder, fname, grand in PASSING:
        p = parse_proposal_file(_demo(folder, fname))
        assert check_math(p) == [], f"{folder} should have no issues"
        assert compute_totals(p)["grand_total"] == grand, folder


def test_failing_demos_report_issues():
    for folder, parts in FAILING:
        p = parse_proposal_file(_demo(folder, *parts))
        assert check_math(p), f"{folder} should report at least one issue"


def test_ci_batch_clean_member_passes():
    p = parse_proposal_file(_demo("09-ci-batch", "proposals", "acme-renewal.yaml"))
    assert check_math(p) == []
    assert compute_totals(p)["grand_total"] == 19800.00


def test_field_aliases_parse():
    p = parse_proposal_file(_demo("06-field-aliases", "proposal.yaml"))
    assert p.vendor == "Pixel & Ink Studio"
    assert p.client == "Thornbury Coffee Roasters Ltd"
    assert len(p.items) == 3
    assert p.items[0].unit_price == 900.0  # 'rate' alias
    assert p.items[2].qty == 8.0           # 'quantity' alias
