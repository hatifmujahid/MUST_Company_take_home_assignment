from __future__ import annotations

from .schemas import ExceptionRecord, ExceptionSeverity, GLCoding, Invoice, MatchResult, MatchStatus

_MATCH_EXCEPTION_MAP = {
    MatchStatus.DUPLICATE: ExceptionSeverity.HIGH,
    MatchStatus.OVER_TOLERANCE: ExceptionSeverity.HIGH,
    MatchStatus.NO_PO_FOUND: ExceptionSeverity.MEDIUM,
    MatchStatus.PARTIAL: ExceptionSeverity.MEDIUM,
}

_SUGGESTED_ACTIONS = {
    MatchStatus.DUPLICATE: "Confirm this hasn't already been paid before processing further.",
    MatchStatus.OVER_TOLERANCE: "Check with the vendor about the amount before paying.",
    MatchStatus.NO_PO_FOUND: "Confirm a PO exists for this purchase, or approve as a non-PO expense.",
    MatchStatus.PARTIAL: "Confirm whether the full order was received before paying in full.",
}


def build_exceptions(
    invoice: Invoice,
    match_result: MatchResult,
    gl_codings: list[GLCoding],
    confidence_threshold: float,
    over_approval_threshold: bool,
) -> list[ExceptionRecord]:
    records: list[ExceptionRecord] = []

    if match_result.status != MatchStatus.MATCHED:
        records.append(
            ExceptionRecord(
                reason_code=match_result.status.value,
                explanation=match_result.detail,
                suggested_action=_SUGGESTED_ACTIONS[match_result.status],
                severity=_MATCH_EXCEPTION_MAP[match_result.status],
            )
        )

    if invoice.confidence < confidence_threshold:
        records.append(
            ExceptionRecord(
                reason_code="LOW_CONFIDENCE_EXTRACTION",
                explanation=(
                    f"The system was only {invoice.confidence:.0%} confident it read this invoice correctly"
                    + (f" ({invoice.extraction_notes})" if invoice.extraction_notes else ".")
                ),
                suggested_action="Double-check the extracted fields against the original invoice before proceeding.",
                severity=ExceptionSeverity.MEDIUM,
            )
        )

    low_conf_lines = [c for c in gl_codings if c.confidence < confidence_threshold]
    if low_conf_lines:
        line_descs = ", ".join(str(c.line_item_index) for c in low_conf_lines)
        records.append(
            ExceptionRecord(
                reason_code="LOW_CONFIDENCE_CODING",
                explanation=f"GL coding confidence was low for line item(s) {line_descs}.",
                suggested_action="Review the suggested GL codes for these lines before importing.",
                severity=ExceptionSeverity.LOW,
            )
        )

    if over_approval_threshold:
        records.append(
            ExceptionRecord(
                reason_code="OVER_APPROVAL_THRESHOLD",
                explanation=f"Invoice total ${invoice.total:,.2f} exceeds every configured approver's limit.",
                suggested_action="This needs manual sign-off above the normal approval chain.",
                severity=ExceptionSeverity.MEDIUM,
            )
        )

    return records
