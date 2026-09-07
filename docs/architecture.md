# Architecture

## Data flow

```
inbox/*.pdf|.txt|.eml
  -> ingest.py            raw file -> plain text (pdfplumber for PDFs), content SHA-256 hash
  -> extract.py           Claude call -> ExtractedInvoice (structured, schema-enforced JSON)
  -> match.py + ledger.py 3-way match vs data/pos.csv + data/receipts.csv, dedup vs state ledger
  -> code.py               Claude call -> GLCoding per line item, using data/chart_of_accounts.csv
  -> route.py               rule-based approver assignment, data/approvers.csv + amount thresholds
  -> exceptions.py           aggregates every flag/confidence gap into ExceptionRecord(s)
  -> report.py                writes digest.md, exceptions.md, import_ready.csv, run.jsonl
```

Orchestrated by `pipeline.py::run_pipeline`, invoked by `cli.py` (`python -m ap_os run`).
Each file is processed independently by `pipeline.py::process_invoice_file` - one bad
invoice becomes its own FAILED result, not a crashed batch.

## Why two Claude calls per invoice, not one

Extraction (`extract.py`) and GL coding (`code.py`) are separate calls with separate,
narrow schemas, rather than one call that does everything. Reasons:

- Each call's output is validated against its own pydantic model before the next stage
  runs - a malformed extraction never reaches the coding step.
- GL coding needs the full chart of accounts in context; extraction doesn't. Keeping them
  separate keeps each prompt focused and keeps cost proportional to what each step
  actually needs.
- It matches the two decisions a human actually makes separately when doing this by hand:
  "what does this invoice say" and "which account does this belong to."

Matching, routing, and duplicate detection are **not** delegated to Claude at all - they're
plain Python against the CSV reference data. Amount tolerances, PO lookups, and approval
thresholds have exact right answers; asking a language model to do arithmetic and lookups
it could get wrong, when deterministic code can't get it wrong, is not a good trade.

## Data contracts

Defined once in `schemas.py` (pydantic v2) and reused across every stage:

- `ExtractedInvoice` / `Invoice` - the extraction schema, enforced via Claude's native
  `output_config: {format: {type: "json_schema", schema: ...}}` structured-output feature
  (not a tool-use workaround - this SDK/model generation supports schema-forced JSON output
  directly on `messages.create`).
- `MatchResult` - `status` is one of `MATCHED / PARTIAL / NO_PO_FOUND / DUPLICATE / OVER_TOLERANCE`.
- `GLCoding`, `RoutingDecision`, `ExceptionRecord`, `ProcessingResult` - the rest of the
  pipeline's outputs, all schema-validated before they reach the report layer.

## Human approval points

- Every clean invoice still requires the human to import `import_ready.csv` themselves -
  nothing is pushed into an accounting system automatically.
- Every exception is a recommendation with a suggested action, never an automated decision.
- Extraction or coding confidence below `confidence_threshold` (default 0.75, in
  `config.yaml`) always routes to the exceptions list, even if no rule-based check fired.
- An invoice whose amount exceeds every configured approver's limit is still routed (to the
  highest-limit approver) with an explicit note that it needs sign-off outside the normal chain -
  the system never silently approves anything.

## Reliability

- **Retries** (`reliability.py`): Claude calls retry up to 3 times with exponential backoff
  (1s/2s/4s) on rate-limit, connection, timeout, overloaded, or 5xx errors only - never on
  4xx validation errors, which are real bugs and should surface immediately.
- **Reference data validation** (`validate_reference_data.py`): every run checks `data/*.csv`
  for missing columns, non-numeric amounts, and malformed emails before processing anything,
  failing with a specific row/column error rather than silently misrouting invoices.
- **Idempotency**: successfully processed files move to `processed/<date>/`, so re-running
  the tool on the same inbox is a safe no-op. Duplicate detection keys on a SHA-256 content
  hash plus (vendor, invoice number) - not filename - so a renamed re-submission is still caught.
- **API-down behavior**: a hard failure with a clear message and nothing moved out of
  `inbox/`. No degraded mode - for a financial tool, stopping cleanly beats guessing.

## Storage

Flat files only - `data/*.csv` (reference data), `state/ledger.jsonl` (append-only dedup/audit
log), `output/<date>/` (per-run digest, exceptions, CSV, and `run.jsonl` log). No database;
volume (<50 invoices/month) doesn't justify one, and flat files are something a non-developer
can open and inspect directly.

## Config & secrets

`config.yaml` (thresholds, model name, paths) and `.env` (`ANTHROPIC_API_KEY`) are both
gitignored; only `config.example.yaml` and `.env.example` are tracked. `setup.bat` creates
the real copies on first run and never touches the tracked templates.

## Non-goals (v1 scope)

- No live QuickBooks/Xero/NetSuite API integration - `import_ready.csv` is a standard
  journal-import shape the human brings in themselves.
- No email/IMAP polling - files are dropped into a watched folder.
- No custom OCR - born-digital PDFs and text/email exports only; a scanned image is a
  known, explicit failure case (`COULD_NOT_PROCESS`), not silently mishandled.
- No auto-approval or auto-payment.
- No Slack/email delivery of the digest - it's a local file, opened automatically.
- Single currency, single entity.
