# Demo 02 — Clean monthly SaaS retainer (passes the gate)

A recurring managed-services retainer that reconciles exactly. Use this as the
template for a proposal you intend to ship: every stated line `total` matches
`qty * unit_price`, and the stated `pricing.total` matches the computed grand
total, so the math gate is green and CI exits 0.

## Input

`proposal.yaml` — Northwind Cloud Services billing Brightline Logistics for a
month-to-month managed SaaS platform: fixed hosting, 40 retainer support hours,
and a 24x7 on-call tier. A 5% loyalty discount, no tax (services-only in a
no-sales-tax jurisdiction).

## Run it

```bash
# Gate the math (CI). Exits 0 because everything reconciles.
python -m pactgen build demos/02-clean-saas-retainer/proposal.yaml --check

# Render the client-ready HTML.
python -m pactgen build demos/02-clean-saas-retainer/proposal.yaml -o retainer.html

# Export to CSV for the accounting system / spreadsheet import.
python -m pactgen build demos/02-clean-saas-retainer/proposal.yaml --format csv -o retainer.csv
```

## Expected result

- Subtotal **12,300.00** (4,200 + 6,600 + 1,500).
- 5% discount **-615.00** -> taxable **11,685.00**, no tax.
- Grand total **11,685.00 USD**, matching the stated `pricing.total`.
- Math check: **OK**, exit code **0**.

## How to act

This is the green baseline. Bump `qty` on the retainer-hours line each month,
re-run `--check`, and only ship when the gate stays green.
