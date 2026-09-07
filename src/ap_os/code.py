from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import anthropic

from .reliability import with_retries
from .schemas import GLCoding, Invoice
from .util import extract_json_text

CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "codings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "line_item_index": {"type": "integer"},
                    "gl_code": {"type": "string"},
                    "gl_account_name": {"type": "string"},
                    "confidence": {"type": "number"},
                    "rationale": {"type": "string"},
                },
                "required": ["line_item_index", "gl_code", "gl_account_name", "confidence", "rationale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["codings"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You assign general ledger (GL) codes to invoice line items for a small business, "
    "using only the chart of accounts provided. Never invent a GL code that isn't in the "
    "chart of accounts. If a line item doesn't clearly fit any account, pick the closest "
    "reasonable match and set confidence low (below 0.6) rather than guessing with false certainty."
)


def load_chart_of_accounts(data_dir: Path) -> list[dict]:
    with open(data_dir / "chart_of_accounts.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def code_invoice(
    client: anthropic.Anthropic, model: str, invoice: Invoice, chart_of_accounts: list[dict]
) -> tuple[list[GLCoding], dict]:
    chart_text = "\n".join(
        f"- {row['gl_code']}: {row['account_name']} - {row['description']}" for row in chart_of_accounts
    )
    items_text = "\n".join(
        f"{i}. {li.description} (qty {li.quantity} @ ${li.unit_price:.2f} = ${li.amount:.2f})"
        for i, li in enumerate(invoice.line_items)
    )

    def _call():
        return client.messages.create(
            model=model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": CODE_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Chart of accounts:\n{chart_text}\n\n"
                        f"Vendor: {invoice.vendor_name}\n\n"
                        f"Line items to code:\n{items_text}\n\n"
                        "Return one coding entry per line item, matched by line_item_index."
                    ),
                }
            ],
        )

    start = time.monotonic()
    response = with_retries(_call, label="code_invoice")
    latency_ms = int((time.monotonic() - start) * 1000)

    data = json.loads(extract_json_text(response))
    codings = [GLCoding.model_validate(c) for c in data["codings"]]
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_ms": latency_ms,
    }
    return codings, usage
