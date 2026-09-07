from __future__ import annotations

import csv
import re
from pathlib import Path

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ReferenceDataError(ValueError):
    """Raised with a specific, actionable message so bad reference data fails loudly, not silently."""


def _require_columns(rows: list[dict], required: list[str], filename: str) -> None:
    if not rows:
        raise ReferenceDataError(f"{filename} is empty - it needs at least a header row and one data row.")
    missing = [c for c in required if c not in rows[0]]
    if missing:
        raise ReferenceDataError(f"{filename} is missing required column(s): {', '.join(missing)}")


def _require_numeric(rows: list[dict], column: str, filename: str) -> None:
    for i, row in enumerate(rows, start=2):  # header is row 1
        value = row.get(column, "")
        try:
            float(value)
        except (TypeError, ValueError):
            raise ReferenceDataError(f"{filename} row {i}: {column} is not numeric ({value!r})")


def _require_nonempty(rows: list[dict], column: str, filename: str) -> None:
    for i, row in enumerate(rows, start=2):
        if not row.get(column, "").strip():
            raise ReferenceDataError(f"{filename} row {i}: {column} is empty")


def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise ReferenceDataError(f"{path.name} does not exist in {path.parent} - copy it from the .example.csv template.")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate_all(data_dir: Path) -> None:
    pos = _read_csv(data_dir / "pos.csv")
    _require_columns(pos, ["po_number", "vendor_name", "po_amount", "po_date"], "pos.csv")
    _require_nonempty(pos, "po_number", "pos.csv")
    _require_numeric(pos, "po_amount", "pos.csv")

    receipts = _read_csv(data_dir / "receipts.csv")
    _require_columns(receipts, ["po_number", "receipt_amount", "receipt_date"], "receipts.csv")
    _require_nonempty(receipts, "po_number", "receipts.csv")
    _require_numeric(receipts, "receipt_amount", "receipts.csv")

    approvers = _read_csv(data_dir / "approvers.csv")
    _require_columns(approvers, ["approver_name", "approver_email", "max_amount"], "approvers.csv")
    _require_numeric(approvers, "max_amount", "approvers.csv")
    for i, row in enumerate(approvers, start=2):
        email = row.get("approver_email", "")
        if not EMAIL_RE.match(email):
            raise ReferenceDataError(f"approvers.csv row {i}: approver_email is not a valid email ({email!r})")
    if not approvers:
        raise ReferenceDataError("approvers.csv has no approvers configured - at least one is required for routing.")

    chart = _read_csv(data_dir / "chart_of_accounts.csv")
    _require_columns(chart, ["gl_code", "account_name", "description"], "chart_of_accounts.csv")
    _require_nonempty(chart, "gl_code", "chart_of_accounts.csv")
