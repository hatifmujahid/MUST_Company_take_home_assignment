"""
The "simple ChatGPT use" baseline required by the brief: dump the invoice plus all the
same reference data (POs, receipts, chart of accounts, approvers) into a single freeform
prompt and ask Claude to decide everything itself in one shot - no schema enforcement, no
fuzzy-match code, no tolerance math, no dedup ledger. This isolates what the engineered
pipeline's decomposition and deterministic business logic actually buys over "just ask the
model", using the same underlying model and the same information both times.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ap_os.util import extract_json_text  # noqa: E402

BASELINE_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor_name": {"type": "string"},
        "invoice_number": {"type": "string"},
        "total": {"type": "number"},
        "ready_to_pay": {"type": "boolean"},
        "gl_code": {"type": "string"},
        "approver_name": {"type": "string"},
        "issues": {"type": "string"},
    },
    "required": ["vendor_name", "invoice_number", "total", "ready_to_pay", "gl_code", "approver_name", "issues"],
    "additionalProperties": False,
}

PROMPT_TEMPLATE = """Here is an invoice that just came in for our small business, plus all our
reference data. Decide whether it's ready to pay, which GL code fits best, who should
approve it, and note any issues (duplicate, doesn't match a PO, amount doesn't match,
receipt doesn't match, etc). Do all of this yourself from the data below.

INVOICE:
{invoice_text}

PURCHASE ORDERS ON FILE:
{pos_text}

RECEIPTS ON FILE:
{receipts_text}

CHART OF ACCOUNTS:
{chart_text}

APPROVERS (name, email, max approval amount):
{approvers_text}

PREVIOUSLY PROCESSED INVOICES (for duplicate checking):
{ledger_text}
"""


def _read_csv_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_naive_baseline(client: anthropic.Anthropic, model: str, invoice_text: str, data_dir: Path, previously_processed: list[str]) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        invoice_text=invoice_text,
        pos_text=_read_csv_text(data_dir / "pos.csv"),
        receipts_text=_read_csv_text(data_dir / "receipts.csv"),
        chart_text=_read_csv_text(data_dir / "chart_of_accounts.csv"),
        approvers_text=_read_csv_text(data_dir / "approvers.csv"),
        ledger_text="\n".join(previously_processed) or "(none yet)",
    )
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        output_config={"format": {"type": "json_schema", "schema": BASELINE_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(extract_json_text(response))


if __name__ == "__main__":
    client = anthropic.Anthropic()
    invoice_path = ROOT / "eval" / "test_cases" / "TC01_clean_matched_simple.txt"
    result = run_naive_baseline(client, "claude-sonnet-5", invoice_path.read_text(encoding="utf-8"), ROOT / "data", [])
    print(json.dumps(result, indent=2))
