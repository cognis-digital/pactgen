# Demo 09 — Batch-gate a folder of proposals in CI (one fails)

The real CI pattern: a directory of proposal specs that must all reconcile
before any of them ship. PACTGEN's non-zero exit on a bad spec lets a single
loop fail the pipeline and name the offender.

## Input

`proposals/` holds two specs from Northwind Cloud Services:
- `acme-renewal.yaml` — clean; subtotal 22,000, 10% discount, grand **19,800.00**.
- `brightline-expansion.yaml` — the migration line states `4000` but
  `24 * 165 = 3960`, so it **fails**.

## Run it

```bash
# Gate every spec; stop the loop on the first failure with a clear message.
for f in demos/09-ci-batch/proposals/*.yaml; do
  echo "checking $f"
  python -m pactgen build "$f" --check || { echo "FAILED: $f"; exit 1; }
done
```

Equivalent GitHub Actions step:

```yaml
- run: pip install -e .
- run: |
    for f in proposals/*.yaml; do pactgen build "$f" --check || exit 1; done
```

## Expected result

- `acme-renewal.yaml` -> Math check OK, exit 0.
- `brightline-expansion.yaml` -> line mismatch on the migration line
  (expected 3,960.00, found 4,000.00), exit 1.
- The loop prints `FAILED: .../brightline-expansion.yaml` and the job goes red.

## How to act

Fix the migration line to `3960` (or remove its `total:`), re-run the loop, and
the whole batch passes — your "proposals are correct" gate is now enforced.
