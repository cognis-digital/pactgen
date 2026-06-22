# Demo 08 — CSV export for procurement / accounting (passes)

Showcases the `--format csv` exporter. A hardware-plus-labor bill of materials
that needs to land in a procurement spreadsheet and a PO system, not just a PDF.

## Input

`proposal.yaml` — Beacon IT Integrators quoting Polestar Architecture for an
office network refresh: access points, switches, a firewall, cabling, and
install labor. 8% sales tax, no discount, reconciles exactly.

## Run it

```bash
# Print CSV to stdout.
python -m pactgen build demos/08-csv-export/proposal.yaml --format csv

# Or write it to a file for import.
python -m pactgen build demos/08-csv-export/proposal.yaml --format csv -o bom.csv
```

## Expected result

A CSV with a header row, one `item` row per line, then `summary` rows:

```csv
section,name,description,qty,unit_price,total,currency
item,Wi-Fi 6E access points,"Ceiling-mount, PoE",12,329.00,3948.00,USD
...
summary,Subtotal,,,,21296.00,USD
summary,Tax (8%),,,,1703.68,USD
summary,Grand Total,,,,22999.68,USD
```

- Subtotal **21,296.00**, tax **1,703.68**, grand total **22,999.68 USD**.
- Exit code **0** (math reconciles).

## How to act

Open `bom.csv` in any spreadsheet, or pipe it to your ERP importer. The
`section` column lets you filter `item` rows from `summary` rows in one step.
