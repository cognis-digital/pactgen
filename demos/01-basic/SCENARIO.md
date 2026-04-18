# Demo 01 — Basic proposal with a deliberate math error

This demo shows PACTGEN turning a YAML proposal/SOW spec into a verified HTML
document and catching a line-item arithmetic mistake.

## Input

`proposal.yaml` describes a small consulting engagement: a vendor (Greenway
Engineering), a client (Acme Robotics), four billable line items, a 10% discount
and 8.25% tax.

One line item ("UX design") includes an explicit `total:` that does **not** match
`qty * unit_price` — a copy/paste error of the kind PACTGEN exists to catch. The
spec also includes a stated `total:` under `pricing:` that is wrong.

## Run it

```bash
# Validate only (CI gate). Exits non-zero because of the mismatch.
python -m pactgen build demos/01-basic/proposal.yaml --check

# Machine-readable for CI / piping
python -m pactgen build demos/01-basic/proposal.yaml --format json

# Render HTML (still reports the issue)
python -m pactgen build demos/01-basic/proposal.yaml -o /tmp/proposal.html
```

## Expected result

- The computed subtotal of the four lines is **18,000.00**
  (40×150 + 20×200 + 16×125 + 30×200 = 6000 + 4000 + 2000 + 6000).
- After a 10% discount (−1,800.00) the taxable base is 16,200.00; 8.25% tax adds
  1,336.50, for a grand total of **17,536.50 USD**.
- The math check **fails** with two issues:
  1. `UX design` line total mismatch (stated 2,500 vs computed 2,000).
  2. `grand_total` mismatch (stated 18,000 vs computed 17,536.50).
- The CLI exits with code **1** so a CI pipeline blocks the bad proposal.

Fix the stated totals (or remove them) and the check passes with exit code 0.
