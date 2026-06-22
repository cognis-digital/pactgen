# Demo 04 — Fractional pricing, volume discount, cent rounding (passes)

Proves the math gate is deterministic with `.99`/`.50` unit prices and a
percentage discount that produces a fractional cent before rounding. The same
spec always renders the same grand total.

## Input

`proposal.yaml` — Quantle Data quoting Hollis & Brand for a per-seat analytics
subscription: 35 analyst seats at $49.99, 120 viewer seats at $12.50, and 7 data
connectors at $89.00. A 15% volume discount and 7.5% sales tax.

The interesting bit: 15% of the $3,872.65 subtotal is $580.8975, which PACTGEN
rounds to **$580.90** (round-half-to-even on the cent), and the tax base
flows from there.

## Run it

```bash
python -m pactgen build demos/04-discount-rounding/proposal.yaml --check
python -m pactgen build demos/04-discount-rounding/proposal.yaml --format json | \
  python -c "import sys,json; print(json.load(sys.stdin)['totals'])"
```

## Expected result

- Subtotal **3,872.65**.
- Discount 15% **-580.90** -> taxable **3,291.75**.
- Tax 7.5% **+246.88** -> grand total **3,538.63 USD**, matching `pricing.total`.
- Math check: **OK**, exit code **0**.

## How to act

If you change a seat count, re-run `--check`; PACTGEN recomputes and tells you
the new stated `pricing.total` to write back.
