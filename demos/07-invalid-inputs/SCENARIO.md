# Demo 07 — Multiple validation failures from a messy export (fails)

Beyond line-total arithmetic, PACTGEN sanity-checks the inputs themselves. This
draft was pulled from a spreadsheet and carries three independent problems; the
gate reports all of them at once.

## Input

`proposal.yaml` — Lumen Stage & AV's draft event package for Riverside Arts
Foundation. The problems:
1. **Negative quantity** — a returned-fixtures "credit" line was typed as `qty: -3`.
2. **Discount out of range** — `discount_pct: 120` (over 100%).
3. **Grand-total mismatch** — the stated `pricing.total: 9000` matches nothing.

## Run it

```bash
python -m pactgen build demos/07-invalid-inputs/proposal.yaml --check
python -m pactgen build demos/07-invalid-inputs/proposal.yaml --format json | \
  python -c "import sys,json; [print(i['where'],'-',i['message']) for i in json.load(sys.stdin)['issues']]"
```

## Expected result

- Three issues reported:
  - `Lighting credit` — Negative quantity (found -3).
  - `discount_pct` — Discount % out of range 0..100 (found 120).
  - `grand_total` — Stated grand total does not match computed (found 9,000.00).
- Math check: **FAILED**, exit code **1**.

## How to act

Make the credit a negative `unit_price` on a positive quantity (or a separate
discount line), set a sane `discount_pct`, and either fix or drop the stated
`pricing.total`. Re-run `--check` until it is green before sending.
