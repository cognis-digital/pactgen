# Demo 06 — Field aliases and nested vendor/client maps (passes)

PACTGEN is forgiving about the spec dialect. This quote uses the alternate field
names many people reach for first, and structured `vendor:`/`client:` maps.

## Input

`proposal.yaml` — Pixel & Ink Studio quoting Thornbury Coffee Roasters for a
one-off brand kit. Instead of `name`/`qty`/`unit_price` it uses
`item`/`quantity`/`rate`; `vendor` and `client` are maps with a `name:` key.
Currency is GBP, with 20% UK VAT and no stated totals.

Accepted aliases:
- item name: `name`, `item`
- quantity: `qty`, `quantity`
- unit price: `unit_price`, `price`, `rate`
- party: a bare string **or** a map with `name:`

## Run it

```bash
python -m pactgen build demos/06-field-aliases/proposal.yaml --check
python -m pactgen build demos/06-field-aliases/proposal.yaml -o quote.html
```

## Expected result

- Subtotal **1,630.00** (900 + 450 + 8x35).
- VAT 20% **+326.00** -> grand total **1,956.00 GBP** (rendered as `£1,956.00`).
- Math check: **OK**, exit code **0**.

## How to act

Mix and match the field names your team already uses — no need to normalize a
spreadsheet export before feeding it to PACTGEN.
