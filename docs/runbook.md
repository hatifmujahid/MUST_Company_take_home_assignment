# Operator Runbook

## Daily routine

1. Drop invoice files into `inbox/` as they come in.
2. Double-click `run.bat`.
3. Read the top line of the digest that opens. If it says "0 need your attention", open `import_ready.csv` and bring it into your accounting software.
4. If it says invoices need attention, open `exceptions.md` and work through them - each one has a plain-English explanation and a suggested next action.
5. Processed files move automatically into `processed/<date>/` - you don't need to clean up `inbox/` yourself.

## What each exception means and how to resolve it

| Reason code | What it means | What to do |
|---|---|---|
| `NO_PO_FOUND` | No PO number was found, or the PO number on the invoice doesn't match anything on file. | Confirm a PO should exist and add it to `data/pos.csv`, or approve as a one-off non-PO expense. |
| `PARTIAL` | The invoice matches a PO, but the receipt on file doesn't match (often a partial shipment). | Confirm how much was actually received before paying the full amount. |
| `OVER_TOLERANCE` | The invoice amount is meaningfully different from its PO. | Check with the vendor before paying - this is not a rounding difference. |
| `DUPLICATE` | This invoice (by content or by vendor+invoice number) has already been processed. | Confirm it hasn't already been paid before doing anything else. |
| `LOW_CONFIDENCE_EXTRACTION` | The system wasn't confident it read the invoice correctly. | Compare the extracted fields against the original file before proceeding. |
| `LOW_CONFIDENCE_CODING` | The system wasn't confident about the suggested GL code for a line item. | Pick the correct GL code yourself for that line before importing. |
| `OVER_APPROVAL_THRESHOLD` | The amount is above every configured approver's limit. | Needs manual sign-off outside the normal approval chain. |
| `COULD_NOT_PROCESS` | The file itself couldn't be read (corrupted, or a scanned image with no extractable text). | Re-save or re-scan the file as a real PDF or text export, then drop it back into `inbox/`. |

## Updating reference data

All of it lives in `data/` as plain CSV files you can open in Excel/Sheets:

- **`pos.csv`** - one row per purchase order: `po_number, vendor_name, po_amount, po_date`.
- **`receipts.csv`** - one row per received shipment/service: `po_number, receipt_amount, receipt_date`.
- **`approvers.csv`** - one row per approver, sorted automatically by limit: `approver_name, approver_email, max_amount`.
- **`chart_of_accounts.csv`** - your GL codes: `gl_code, account_name, description`. The description is what the system uses to decide which code fits a line item, so keep it specific.

The tool checks these files for obvious problems (missing columns, non-numeric amounts, bad emails) every time it runs, and will stop with a specific error message rather than silently misrouting an invoice if something's wrong.

## If something goes wrong

- **"Reference data problem, nothing was processed"** - one of the CSV files in `data/` has a formatting problem. The error message names the exact file, row, and column.
- **The tool can't reach Claude at all** - it will say so plainly and nothing will be moved out of `inbox/`. Just try again in a few minutes.
- **A single invoice fails** - it's reported as its own exception in `exceptions.md` and doesn't stop the rest of the batch from processing.
