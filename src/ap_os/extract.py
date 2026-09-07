from __future__ import annotations

import json
import time

import anthropic

from .reliability import with_retries
from .schemas import ExtractedInvoice
from .util import extract_json_text

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor_name": {"type": "string"},
        "invoice_number": {"type": "string"},
        "invoice_date": {"type": ["string", "null"], "description": "ISO 8601 date, YYYY-MM-DD"},
        "due_date": {"type": ["string", "null"], "description": "ISO 8601 date, YYYY-MM-DD"},
        "po_number": {"type": ["string", "null"]},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "amount": {"type": "number"},
                },
                "required": ["description", "quantity", "unit_price", "amount"],
                "additionalProperties": False,
            },
        },
        "subtotal": {"type": ["number", "null"]},
        "tax": {"type": ["number", "null"]},
        "total": {"type": "number"},
        "currency": {"type": "string"},
        "confidence": {
            "type": "number",
            "description": "Your own confidence (0-1) that every field above is correct and complete.",
        },
        "extraction_notes": {
            "type": ["string", "null"],
            "description": "Anything ambiguous, illegible, or assumed while extracting.",
        },
    },
    "required": [
        "vendor_name",
        "invoice_number",
        "line_items",
        "total",
        "currency",
        "confidence",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You extract structured data from accounts-payable invoices for a small business. "
    "Extract exactly what is on the document - never invent a PO number, date, or line item "
    "that isn't present. If the PO number is genuinely absent, return null for po_number. "
    "Set confidence honestly: lower it whenever the layout is messy, a field is ambiguous, "
    "or you had to infer something instead of reading it directly."
)


def extract_invoice(client: anthropic.Anthropic, model: str, raw_text: str) -> tuple[ExtractedInvoice, dict]:
    def _call():
        return client.messages.create(
            model=model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": EXTRACT_SCHEMA}},
            messages=[{"role": "user", "content": f"Invoice text:\n\n{raw_text}"}],
        )

    start = time.monotonic()
    response = with_retries(_call, label="extract_invoice")
    latency_ms = int((time.monotonic() - start) * 1000)

    data = json.loads(extract_json_text(response))
    invoice = ExtractedInvoice.model_validate(data)
    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_ms": latency_ms,
    }
    return invoice, usage
