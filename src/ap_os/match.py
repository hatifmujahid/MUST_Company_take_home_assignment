from __future__ import annotations

import csv
import difflib
from dataclasses import dataclass
from pathlib import Path

from .schemas import Invoice, MatchResult, MatchStatus


@dataclass
class PORecord:
    po_number: str
    vendor_name: str
    amount: float
    date: str


@dataclass
class ReceiptRecord:
    po_number: str
    receipt_amount: float
    receipt_date: str


def _normalize(s: str) -> str:
    return "".join(ch for ch in s.strip().lower() if ch.isalnum())


def load_pos(data_dir: Path) -> dict[str, PORecord]:
    records: dict[str, PORecord] = {}
    with open(data_dir / "pos.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rec = PORecord(
                po_number=row["po_number"].strip(),
                vendor_name=row["vendor_name"].strip(),
                amount=float(row["po_amount"]),
                date=row["po_date"].strip(),
            )
            records[_normalize(rec.po_number)] = rec
    return records


def load_receipts(data_dir: Path) -> dict[str, ReceiptRecord]:
    records: dict[str, ReceiptRecord] = {}
    with open(data_dir / "receipts.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rec = ReceiptRecord(
                po_number=row["po_number"].strip(),
                receipt_amount=float(row["receipt_amount"]),
                receipt_date=row["receipt_date"].strip(),
            )
            records[_normalize(rec.po_number)] = rec
    return records


def _find_po(po_number: str, pos: dict[str, PORecord]) -> PORecord | None:
    key = _normalize(po_number)
    if key in pos:
        return pos[key]
    close = difflib.get_close_matches(key, pos.keys(), n=1, cutoff=0.8)
    if close:
        return pos[close[0]]
    return None


def match_invoice(
    invoice: Invoice,
    pos: dict[str, PORecord],
    receipts: dict[str, ReceiptRecord],
    is_duplicate: bool,
    tolerance_pct: float,
    tolerance_abs: float,
) -> MatchResult:
    if is_duplicate:
        return MatchResult(
            status=MatchStatus.DUPLICATE,
            invoice_amount=invoice.total,
            detail=(
                f"An invoice with this content or invoice number ({invoice.invoice_number}) "
                "has already been processed."
            ),
        )

    if not invoice.po_number:
        return MatchResult(
            status=MatchStatus.NO_PO_FOUND,
            invoice_amount=invoice.total,
            detail="No PO number was found on this invoice.",
        )

    po = _find_po(invoice.po_number, pos)
    if po is None:
        return MatchResult(
            status=MatchStatus.NO_PO_FOUND,
            invoice_amount=invoice.total,
            po_number=invoice.po_number,
            detail=f"PO number '{invoice.po_number}' does not match any PO on file.",
        )

    tolerance = max(tolerance_abs, tolerance_pct * po.amount)
    variance = round(invoice.total - po.amount, 2)

    if abs(variance) > tolerance:
        return MatchResult(
            status=MatchStatus.OVER_TOLERANCE,
            po_number=po.po_number,
            po_amount=po.amount,
            invoice_amount=invoice.total,
            variance=variance,
            detail=(
                f"Invoice total ${invoice.total:,.2f} differs from PO {po.po_number} "
                f"(${po.amount:,.2f}) by ${abs(variance):,.2f}, outside the ${tolerance:,.2f} tolerance."
            ),
        )

    receipt = receipts.get(_normalize(po.po_number))
    if receipt is None:
        return MatchResult(
            status=MatchStatus.PARTIAL,
            po_number=po.po_number,
            po_amount=po.amount,
            invoice_amount=invoice.total,
            variance=variance,
            detail=f"Invoice matches PO {po.po_number}, but no receipt is on file yet to confirm goods/services were received.",
        )

    receipt_variance = round(receipt.receipt_amount - po.amount, 2)
    if abs(receipt_variance) > tolerance:
        return MatchResult(
            status=MatchStatus.PARTIAL,
            po_number=po.po_number,
            po_amount=po.amount,
            receipt_amount=receipt.receipt_amount,
            invoice_amount=invoice.total,
            variance=receipt_variance,
            detail=(
                f"Receipt on file (${receipt.receipt_amount:,.2f}) doesn't match PO {po.po_number} "
                f"(${po.amount:,.2f}) - looks like a partial shipment/delivery."
            ),
        )

    return MatchResult(
        status=MatchStatus.MATCHED,
        po_number=po.po_number,
        po_amount=po.amount,
        receipt_amount=receipt.receipt_amount,
        invoice_amount=invoice.total,
        variance=variance,
        detail=f"Invoice, PO {po.po_number}, and receipt all agree within tolerance.",
    )
