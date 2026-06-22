"""Core engine for PACTGEN.

Parses a minimal, dependency-free YAML subset (the common case used by
proposals: scalars, nested maps, and lists of maps), models the proposal,
validates line-item arithmetic against a small floating tolerance, computes
totals (subtotal -> discount -> tax -> grand total), and renders HTML.

No third-party imports. Python 3.10+.
"""

from __future__ import annotations

import csv
import html
import io
import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

# Money is compared with a small tolerance so 19.99*3 style rounding is tolerated.
CENT = 0.005

TOOL_NAME = "pactgen"


def _read_version() -> str:
    """Resolve the tool version from the repo VERSION file, with a safe default."""
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (
        os.path.join(here, "..", "VERSION"),
        os.path.join(here, "VERSION"),
    ):
        try:
            with open(cand, "r", encoding="utf-8") as fh:
                v = fh.read().strip()
            if v:
                return v
        except OSError:
            continue
    return "0.3.8"


TOOL_VERSION = _read_version()


# --------------------------------------------------------------------------- #
# Minimal YAML subset parser (stdlib only).
# Supports: key: value, nested 2-space-indented maps, and lists of maps
# introduced by "- key: value" entries. Values are coerced to int/float/bool.
# --------------------------------------------------------------------------- #

def _coerce(raw: str) -> Any:
    s = raw.strip()
    if s == "" or s in ("~", "null", "None"):
        return None
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    low = s.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    # number? allow $ and thousands separators on money-ish values
    cleaned = s.replace("$", "").replace(",", "")
    if re.fullmatch(r"-?\d+", cleaned):
        return int(cleaned)
    if re.fullmatch(r"-?\d*\.\d+", cleaned):
        return float(cleaned)
    return s


def _strip_comment(line: str) -> str:
    # Remove trailing comments not inside quotes (simple state machine).
    out = []
    q = None
    for ch in line:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out)


def parse_yaml(text: str) -> dict:
    """Parse the supported YAML subset into nested dict/list structures."""
    lines = []
    for raw in text.splitlines():
        body = _strip_comment(raw).rstrip()
        if body.strip() == "":
            continue
        indent = len(body) - len(body.lstrip(" "))
        lines.append((indent, body.strip()))

    pos = 0

    def parse_block(min_indent: int):
        nonlocal pos
        # Decide list vs map by first line at this indent.
        if pos >= len(lines):
            return {}
        indent, content = lines[pos]
        if content.startswith("- ") or content == "-":
            return parse_list(indent)
        return parse_map(indent)

    def parse_map(indent: int) -> dict:
        nonlocal pos
        result: dict = {}
        while pos < len(lines):
            cur_indent, content = lines[pos]
            if cur_indent < indent:
                break
            if cur_indent > indent:
                # Shouldn't happen for a well-formed map; skip defensively.
                pos += 1
                continue
            if content.startswith("- "):
                break
            if ":" not in content:
                pos += 1
                continue
            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            pos += 1
            if val == "":
                # Nested block (map or list) on following deeper lines.
                if pos < len(lines) and lines[pos][0] > indent:
                    result[key] = parse_block(lines[pos][0])
                else:
                    result[key] = None
            else:
                result[key] = _coerce(val)
        return result

    def parse_list(indent: int) -> list:
        nonlocal pos
        items: list = []
        while pos < len(lines):
            cur_indent, content = lines[pos]
            if cur_indent < indent or not (content.startswith("- ") or content == "-"):
                break
            inner = content[1:].strip()  # drop leading '-'
            pos += 1
            if inner == "":
                # Block item on deeper lines.
                if pos < len(lines) and lines[pos][0] > indent:
                    items.append(parse_block(lines[pos][0]))
                else:
                    items.append(None)
            elif ":" in inner:
                # Inline first key of a map item; reparse as a synthetic map.
                key, _, val = inner.partition(":")
                obj = {key.strip(): _coerce(val.strip()) if val.strip() else None}
                # Continuation keys are indented deeper than the dash.
                while pos < len(lines) and lines[pos][0] > indent:
                    k2, c2 = lines[pos]
                    if c2.startswith("- "):
                        break
                    kk, _, vv = c2.partition(":")
                    pos += 1
                    vv = vv.strip()
                    if vv == "" and pos < len(lines) and lines[pos][0] > k2:
                        obj[kk.strip()] = parse_block(lines[pos][0])
                    else:
                        obj[kk.strip()] = _coerce(vv)
                items.append(obj)
            else:
                items.append(_coerce(inner))
        return items

    return parse_map(0) if lines else {}


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass
class LineItem:
    name: str
    qty: float
    unit_price: float
    description: str = ""
    # Optional explicitly-stated total to validate against computed total.
    stated_total: float | None = None

    @property
    def computed_total(self) -> float:
        return round(self.qty * self.unit_price, 2)


@dataclass
class MathIssue:
    where: str
    message: str
    expected: float
    found: float

    def to_dict(self) -> dict:
        return {
            "where": self.where,
            "message": self.message,
            "expected": round(self.expected, 2),
            "found": round(self.found, 2),
        }


@dataclass
class Proposal:
    title: str = "Proposal"
    client: str = ""
    vendor: str = ""
    date: str = field(default_factory=lambda: date.today().isoformat())
    currency: str = "USD"
    notes: str = ""
    items: list[LineItem] = field(default_factory=list)
    discount_pct: float = 0.0
    tax_pct: float = 0.0
    # Optional stated grand total to validate against.
    stated_total: float | None = None


# --------------------------------------------------------------------------- #
# Parsing into the model
# --------------------------------------------------------------------------- #

def _num(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    if isinstance(v, bool):
        return default
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace("$", "").replace(",", ""))
    except ValueError:
        return default


def parse_proposal(text: str) -> Proposal:
    """Parse a YAML-subset proposal spec into a Proposal."""
    data = parse_yaml(text)
    if not isinstance(data, dict):
        raise ValueError("Proposal spec must be a mapping at the top level.")

    pricing = data.get("pricing") or {}
    if not isinstance(pricing, dict):
        pricing = {}

    raw_items = data.get("items")
    if raw_items is None:
        raw_items = pricing.get("items")
    items: list[LineItem] = []
    if isinstance(raw_items, list):
        for idx, it in enumerate(raw_items):
            if not isinstance(it, dict):
                raise ValueError(f"items[{idx}] must be a mapping.")
            name = str(it.get("name") or it.get("item") or f"Item {idx + 1}")
            qty = _num(it.get("qty", it.get("quantity", 1)), 1.0)
            unit = _num(it.get("unit_price", it.get("price", it.get("rate", 0))), 0.0)
            stated = it.get("total")
            items.append(
                LineItem(
                    name=name,
                    qty=qty,
                    unit_price=unit,
                    description=str(it.get("description", "") or ""),
                    stated_total=_num(stated) if stated is not None else None,
                )
            )
    if not items:
        raise ValueError("Proposal has no line items (expected a non-empty 'items' list).")

    client = data.get("client")
    if isinstance(client, dict):
        client = client.get("name", "")
    vendor = data.get("vendor")
    if isinstance(vendor, dict):
        vendor = vendor.get("name", "")

    stated_total = pricing.get("total", data.get("total"))

    return Proposal(
        title=str(data.get("title", "Proposal")),
        client=str(client or ""),
        vendor=str(vendor or ""),
        date=str(data.get("date") or date.today().isoformat()),
        currency=str(data.get("currency", "USD")),
        notes=str(data.get("notes", "") or ""),
        items=items,
        discount_pct=_num(pricing.get("discount_pct", data.get("discount_pct", 0)), 0.0),
        tax_pct=_num(pricing.get("tax_pct", data.get("tax_pct", 0)), 0.0),
        stated_total=_num(stated_total) if stated_total is not None else None,
    )


def parse_proposal_file(path: str) -> Proposal:
    with open(path, "r", encoding="utf-8") as fh:
        return parse_proposal(fh.read())


# --------------------------------------------------------------------------- #
# Math
# --------------------------------------------------------------------------- #

def compute_totals(p: Proposal) -> dict:
    """Return subtotal, discount, taxable, tax, and grand total."""
    subtotal = round(sum(i.computed_total for i in p.items), 2)
    discount = round(subtotal * (p.discount_pct / 100.0), 2)
    taxable = round(subtotal - discount, 2)
    tax = round(taxable * (p.tax_pct / 100.0), 2)
    grand_total = round(taxable + tax, 2)
    return {
        "subtotal": subtotal,
        "discount": discount,
        "taxable": taxable,
        "tax": tax,
        "grand_total": grand_total,
    }


def check_math(p: Proposal) -> list[MathIssue]:
    """Validate any stated line totals and the stated grand total."""
    issues: list[MathIssue] = []
    for i in p.items:
        if i.qty < 0:
            issues.append(MathIssue(i.name, "Negative quantity", 0.0, i.qty))
        if i.unit_price < 0:
            issues.append(MathIssue(i.name, "Negative unit price", 0.0, i.unit_price))
        if i.stated_total is not None:
            if abs(i.stated_total - i.computed_total) > CENT:
                issues.append(
                    MathIssue(
                        i.name,
                        f"Line total mismatch (qty {i.qty} x {i.unit_price})",
                        i.computed_total,
                        i.stated_total,
                    )
                )
    if p.discount_pct < 0 or p.discount_pct > 100:
        issues.append(MathIssue("discount_pct", "Discount % out of range 0..100", 0.0, p.discount_pct))
    if p.tax_pct < 0:
        issues.append(MathIssue("tax_pct", "Negative tax %", 0.0, p.tax_pct))

    totals = compute_totals(p)
    if p.stated_total is not None:
        if abs(p.stated_total - totals["grand_total"]) > CENT:
            issues.append(
                MathIssue(
                    "grand_total",
                    "Stated grand total does not match computed total",
                    totals["grand_total"],
                    p.stated_total,
                )
            )
    return issues


# --------------------------------------------------------------------------- #
# Serialization / rendering
# --------------------------------------------------------------------------- #

def proposal_to_dict(p: Proposal) -> dict:
    totals = compute_totals(p)
    issues = check_math(p)
    return {
        "title": p.title,
        "client": p.client,
        "vendor": p.vendor,
        "date": p.date,
        "currency": p.currency,
        "notes": p.notes,
        "discount_pct": p.discount_pct,
        "tax_pct": p.tax_pct,
        "items": [
            {
                "name": i.name,
                "description": i.description,
                "qty": i.qty,
                "unit_price": round(i.unit_price, 2),
                "total": i.computed_total,
            }
            for i in p.items
        ],
        "totals": totals,
        "issues": [iss.to_dict() for iss in issues],
        "ok": len(issues) == 0,
    }


def render_csv(p: Proposal) -> str:
    """Render the proposal line items + totals as CSV.

    Useful for importing into a spreadsheet, an ERP, or an accounting tool.
    One row per line item, then blank-keyed summary rows for the totals so the
    whole document round-trips into a single sheet.
    """
    totals = compute_totals(p)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["section", "name", "description", "qty", "unit_price", "total", "currency"])
    for i in p.items:
        w.writerow([
            "item",
            i.name,
            i.description,
            f"{i.qty:g}",
            f"{i.unit_price:.2f}",
            f"{i.computed_total:.2f}",
            p.currency,
        ])
    w.writerow(["summary", "Subtotal", "", "", "", f"{totals['subtotal']:.2f}", p.currency])
    if p.discount_pct:
        w.writerow([
            "summary", f"Discount ({p.discount_pct:g}%)", "", "", "",
            f"{-totals['discount']:.2f}", p.currency,
        ])
    if p.tax_pct:
        w.writerow([
            "summary", f"Tax ({p.tax_pct:g}%)", "", "", "",
            f"{totals['tax']:.2f}", p.currency,
        ])
    w.writerow(["summary", "Grand Total", "", "", "", f"{totals['grand_total']:.2f}", p.currency])
    return buf.getvalue()


def _money(v: float, currency: str) -> str:
    sym = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency.upper(), "")
    return f"{sym}{v:,.2f}"


def render_html(p: Proposal) -> str:
    """Render a self-contained HTML proposal document."""
    e = html.escape
    totals = compute_totals(p)
    issues = check_math(p)
    cur = p.currency

    rows = []
    for i in p.items:
        desc = f"<div class='desc'>{e(i.description)}</div>" if i.description else ""
        rows.append(
            "<tr>"
            f"<td><strong>{e(i.name)}</strong>{desc}</td>"
            f"<td class='num'>{i.qty:g}</td>"
            f"<td class='num'>{_money(i.unit_price, cur)}</td>"
            f"<td class='num'>{_money(i.computed_total, cur)}</td>"
            "</tr>"
        )

    issue_block = ""
    if issues:
        lis = "".join(
            f"<li>{e(x.where)}: {e(x.message)} "
            f"(expected {x.expected:,.2f}, found {x.found:,.2f})</li>"
            for x in issues
        )
        issue_block = (
            "<div class='issues'><h3>⚠ Math check failed</h3>"
            f"<ul>{lis}</ul></div>"
        )
    else:
        issue_block = "<div class='ok'>✓ Line-item math verified.</div>"

    notes_block = f"<div class='notes'><h3>Notes</h3><p>{e(p.notes)}</p></div>" if p.notes else ""

    def trow(label, value, cls=""):
        return f"<tr class='{cls}'><td>{e(label)}</td><td class='num'>{_money(value, cur)}</td></tr>"

    summary = [trow("Subtotal", totals["subtotal"])]
    if p.discount_pct:
        summary.append(trow(f"Discount ({p.discount_pct:g}%)", -totals["discount"]))
    if p.tax_pct:
        summary.append(trow(f"Tax ({p.tax_pct:g}%)", totals["tax"]))
    summary.append(trow("Total", totals["grand_total"], cls="grand"))

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(p.title)}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
          color:#1a1a1a; max-width:820px; margin:40px auto; padding:0 20px; line-height:1.5; }}
  header {{ border-bottom:3px solid #2b6cb0; padding-bottom:16px; margin-bottom:24px; }}
  h1 {{ margin:0 0 6px; font-size:28px; color:#2b6cb0; }}
  .meta {{ color:#555; font-size:14px; }}
  table {{ width:100%; border-collapse:collapse; margin:18px 0; }}
  th, td {{ padding:10px 12px; text-align:left; border-bottom:1px solid #e2e8f0; }}
  th {{ background:#f7fafc; font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:#4a5568; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .desc {{ color:#666; font-size:13px; margin-top:2px; }}
  .summary {{ width:340px; margin-left:auto; }}
  .summary .grand td {{ font-weight:700; font-size:18px; border-top:2px solid #2b6cb0; border-bottom:none; }}
  .issues {{ background:#fff5f5; border:1px solid #fc8181; border-radius:8px; padding:12px 16px; color:#9b2c2c; }}
  .ok {{ background:#f0fff4; border:1px solid #9ae6b4; border-radius:8px; padding:10px 16px; color:#276749; }}
  .notes {{ margin-top:24px; }}
  footer {{ margin-top:36px; color:#888; font-size:12px; border-top:1px solid #e2e8f0; padding-top:12px; }}
</style></head><body>
<header>
  <h1>{e(p.title)}</h1>
  <div class="meta">
    <strong>From:</strong> {e(p.vendor)} &nbsp;|&nbsp;
    <strong>To:</strong> {e(p.client)} &nbsp;|&nbsp;
    <strong>Date:</strong> {e(p.date)}
  </div>
</header>
<table>
  <thead><tr><th>Item</th><th class="num">Qty</th><th class="num">Unit Price</th><th class="num">Total</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>
<table class="summary">{''.join(summary)}</table>
{issue_block}
{notes_block}
<footer>Generated by PACTGEN — reproducible proposals. Currency: {e(cur)}.</footer>
</body></html>"""
