# Demo 03 — EUR fixed-bid with 19% VAT (passes)

Shows non-USD currency rendering (the € symbol) and a German-style VAT line.
A fixed-price website redesign quoted in euros with 19% Umsatzsteuer.

## Input

`proposal.yaml` — Atelier Drei GmbH quoting Café Mauerblume for a website
redesign and headless-CMS migration. Four fixed line items, no discount, 19%
VAT. `currency: EUR` makes PACTGEN render totals with a `€` prefix in HTML.

## Run it

```bash
python -m pactgen build demos/03-eur-fixed-bid/proposal.yaml --check
python -m pactgen build demos/03-eur-fixed-bid/proposal.yaml -o redesign.html
```

## Expected result

- Subtotal **17,500.00** (3,800 + 3,900 + 7,200 + 2,600).
- VAT 19% **+3,325.00** -> grand total **20,825.00 EUR**, matching `pricing.total`.
- Math check: **OK**, exit code **0**.
- The HTML renders amounts as `€17,500.00` etc.

## How to act

Use as the EUR/VAT template. Swap `currency:` to `GBP` for the `£` symbol; any
unknown currency code falls back to a bare number with no symbol.
