import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pactgen import (  # noqa: E402
    TOOL_NAME,
    TOOL_VERSION,
    parse_proposal,
    parse_proposal_file,
    compute_totals,
    check_math,
    render_html,
    proposal_to_dict,
)
from pactgen.cli import main  # noqa: E402

DEMO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "demos", "01-basic", "proposal.yaml",
)


def test_metadata():
    assert TOOL_NAME == "pactgen"
    assert TOOL_VERSION.count(".") == 2


def test_parse_demo():
    p = parse_proposal_file(DEMO)
    assert p.vendor.startswith("Greenway")
    assert p.client.startswith("Acme")
    assert len(p.items) == 4
    assert p.discount_pct == 10
    assert p.tax_pct == 8.25


def test_totals_are_correct():
    p = parse_proposal_file(DEMO)
    t = compute_totals(p)
    assert t["subtotal"] == 18000.00
    assert t["discount"] == 1800.00
    assert t["taxable"] == 16200.00
    assert t["tax"] == 1336.50
    assert t["grand_total"] == 17536.50


def test_demo_has_two_known_issues():
    p = parse_proposal_file(DEMO)
    issues = check_math(p)
    wheres = sorted(i.where for i in issues)
    assert wheres == ["UX design", "grand_total"]


def test_clean_proposal_passes():
    spec = """\
title: Clean
vendor: A
client: B
items:
  - name: Work
    qty: 3
    unit_price: 100
    total: 300
pricing:
  tax_pct: 10
  total: 330
"""
    p = parse_proposal(spec)
    assert check_math(p) == []
    assert compute_totals(p)["grand_total"] == 330.0


def test_render_html_is_self_contained():
    p = parse_proposal_file(DEMO)
    doc = render_html(p)
    assert doc.startswith("<!DOCTYPE html>")
    assert "Math check failed" in doc  # demo has issues
    assert "17,536.50" in doc
    assert "<script" not in doc.lower()  # no external/inline JS


def test_proposal_to_dict_shape():
    p = parse_proposal_file(DEMO)
    d = proposal_to_dict(p)
    assert d["ok"] is False
    assert len(d["items"]) == 4
    assert d["totals"]["grand_total"] == 17536.50


def test_cli_check_exits_nonzero_on_demo():
    rc = main(["build", DEMO, "--check"])
    assert rc == 1


def test_cli_json_output(capsys):
    rc = main(["build", DEMO, "--format", "json"])
    assert rc == 1
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["totals"]["grand_total"] == 17536.50
    assert data["ok"] is False


def test_cli_writes_html(tmp_path):
    out = tmp_path / "p.html"
    rc = main(["build", DEMO, "-o", str(out)])
    assert rc == 1  # still flags the math issues
    assert out.exists()
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_missing_file_returns_2():
    rc = main(["build", "does_not_exist.yaml", "--check"])
    assert rc == 2
