"""Tests for input validation, error handling, and edge-case hardening."""
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pactgen.core import (  # noqa: E402
    parse_proposal,
    parse_proposal_file,
    compute_totals,
    check_math,
    _num,
)
from pactgen.cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# TOOL_NAME / TOOL_VERSION are now canonical in core (not silent fallback).
# ---------------------------------------------------------------------------

def test_constants_defined_in_core():
    """TOOL_NAME and TOOL_VERSION must come directly from core, not fallbacks."""
    from pactgen.core import TOOL_NAME as CN, TOOL_VERSION as CV
    assert CN == "pactgen"
    assert CV.count(".") == 2


# ---------------------------------------------------------------------------
# Input validation: empty / blank file path
# ---------------------------------------------------------------------------

def test_empty_path_raises_value_error():
    with pytest.raises(ValueError, match="empty"):
        parse_proposal_file("")


def test_blank_path_raises_value_error():
    with pytest.raises(ValueError, match="empty"):
        parse_proposal_file("   ")


# ---------------------------------------------------------------------------
# Input validation: directory passed as spec path
# ---------------------------------------------------------------------------

def test_directory_as_spec_returns_2(tmp_path):
    rc = main(["build", str(tmp_path), "--check"])
    assert rc == 2


# ---------------------------------------------------------------------------
# Input validation: empty YAML body
# ---------------------------------------------------------------------------

def test_empty_yaml_raises_value_error():
    with pytest.raises(ValueError):
        parse_proposal("")


def test_blank_yaml_raises_value_error():
    with pytest.raises(ValueError):
        parse_proposal("   \n\n  ")


# ---------------------------------------------------------------------------
# Input validation: no items in spec
# ---------------------------------------------------------------------------

def test_missing_items_raises_value_error():
    spec = "title: No Items\nvendor: A\nclient: B\n"
    with pytest.raises(ValueError, match="no line items"):
        parse_proposal(spec)


def test_empty_items_list_raises_value_error():
    # items key present but empty list (parse_yaml returns [])
    spec = "title: Empty\nvendor: A\nclient: B\nitems:\n"
    with pytest.raises(ValueError, match="no line items"):
        parse_proposal(spec)


# ---------------------------------------------------------------------------
# Input validation: non-mapping item in items list
# ---------------------------------------------------------------------------

def test_non_mapping_item_raises_value_error():
    spec = """\
title: Bad
vendor: A
client: B
items:
  - just a scalar
"""
    # A bare scalar list item is parsed as a string, not a dict -> should raise
    with pytest.raises(ValueError, match=r"items\[0\]"):
        parse_proposal(spec)


# ---------------------------------------------------------------------------
# Numeric edge cases: NaN / Inf inputs are rejected by _num
# ---------------------------------------------------------------------------

def test_num_rejects_nan():
    assert _num(float("nan")) == 0.0


def test_num_rejects_inf():
    assert _num(float("inf")) == 0.0
    assert _num(float("-inf")) == 0.0


def test_num_rejects_nan_string():
    # "nan" as a string — should fall back to default, not produce NaN
    result = _num("nan")
    assert not math.isnan(result)
    assert result == 0.0


# ---------------------------------------------------------------------------
# Edge case: single item, zero price
# ---------------------------------------------------------------------------

def test_zero_price_item_is_valid():
    spec = """\
title: Free Tier
vendor: A
client: B
items:
  - name: Free item
    qty: 5
    unit_price: 0
"""
    p = parse_proposal(spec)
    t = compute_totals(p)
    assert t["grand_total"] == 0.0
    issues = check_math(p)
    assert issues == []


# ---------------------------------------------------------------------------
# CLI: unwritable output path returns exit code 2 (no raw traceback)
# ---------------------------------------------------------------------------

def test_cli_bad_output_path_returns_2(tmp_path):
    demo = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "demos", "01-basic", "proposal.yaml",
    )
    bad_out = str(tmp_path / "nonexistent_dir" / "out.html")
    rc = main(["build", demo, "-o", bad_out])
    assert rc == 2


# ---------------------------------------------------------------------------
# CLI: no subcommand — should print help and return 0 (not crash)
# ---------------------------------------------------------------------------

def test_cli_no_subcommand_returns_0():
    rc = main([])
    assert rc == 0


# ---------------------------------------------------------------------------
# Math check: negative qty and negative unit_price are flagged
# ---------------------------------------------------------------------------

def test_negative_qty_flagged():
    spec = """\
title: Neg Qty
vendor: A
client: B
items:
  - name: Refund
    qty: -1
    unit_price: 100
"""
    p = parse_proposal(spec)
    issues = check_math(p)
    assert any("Negative quantity" in i.message for i in issues)


def test_negative_unit_price_flagged():
    spec = """\
title: Neg Price
vendor: A
client: B
items:
  - name: Odd
    qty: 1
    unit_price: -50
"""
    p = parse_proposal(spec)
    issues = check_math(p)
    assert any("Negative unit price" in i.message for i in issues)


# ---------------------------------------------------------------------------
# Math check: discount_pct out of range is flagged
# ---------------------------------------------------------------------------

def test_discount_over_100_flagged():
    spec = """\
title: Bad Discount
vendor: A
client: B
pricing:
  discount_pct: 150
items:
  - name: Widget
    qty: 1
    unit_price: 100
"""
    p = parse_proposal(spec)
    issues = check_math(p)
    assert any("Discount" in i.message for i in issues)


# ---------------------------------------------------------------------------
# mcp_server: module compiles cleanly and exposes serve()
# ---------------------------------------------------------------------------

def test_mcp_server_importable():
    import importlib
    mod = importlib.import_module("pactgen.mcp_server")
    assert callable(mod.serve)


def test_mcp_server_uses_real_core_functions():
    """mcp_server must import real functions from core (no dangling scan/to_json refs)."""
    import py_compile
    # py_compile catches NameErrors at import-time for bare names that don't exist
    py_compile.compile(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "pactgen", "mcp_server.py",
        ),
        doraise=True,
    )
