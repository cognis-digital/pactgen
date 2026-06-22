# Demo 05 — T&M SOW with one transcribed line-total error (fails)

A large time-and-materials SOW where exactly one line's stated `total` was
fat-fingered. This is the single most common real failure mode: rate and hours
are right, but the pre-typed line total is stale from an earlier draft.

## Input

`proposal.yaml` — Meridian Analytics Partners' SOW for Cascade Health Systems.
Four labor lines at MSA rates. The **BI enablement** line states a total of
`24000`, but `120 * 175 = 21000`. No discount or tax, and no stated grand
total, so the line mismatch is the only issue.

## Run it

```bash
# CI gate: fails because of the one bad line.
python -m pactgen build demos/05-sow-line-error/proposal.yaml --check

# See exactly which line and the expected vs. found amounts.
python -m pactgen build demos/05-sow-line-error/proposal.yaml --format json | \
  python -c "import sys,json; print(json.load(sys.stdin)['issues'])"
```

## Expected result

- One issue: **BI enablement** line total mismatch — expected **21,000.00**,
  found **24,000.00**.
- Computed subtotal/grand total **86,800.00 USD** (17,200 + 44,400 + 21,000 + 4,200).
- Math check: **FAILED**, exit code **1**.

## How to act

Fix the BI enablement `total:` to `21000` (or delete the `total:` line entirely
and let PACTGEN compute it). Re-run `--check`; the gate goes green.
