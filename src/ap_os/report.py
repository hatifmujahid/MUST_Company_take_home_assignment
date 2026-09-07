from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path

from .schemas import ProcessingResult, ProcessingStatus


def _invoice_ref(result: ProcessingResult) -> str:
    if result.invoice:
        return f"{result.invoice.vendor_name} - Invoice {result.invoice.invoice_number}"
    return result.source_file


def write_reports(results: list[ProcessingResult], output_dir: Path) -> tuple[Path, Path, Path]:
    run_dir = output_dir / date.today().isoformat()
    run_dir.mkdir(parents=True, exist_ok=True)

    digest_path = run_dir / "digest.md"
    exceptions_path = run_dir / "exceptions.md"
    csv_path = run_dir / "import_ready.csv"
    run_log_path = run_dir / "run.jsonl"

    clean = [r for r in results if r.status == ProcessingStatus.CLEAN]
    flagged = [r for r in results if r.status == ProcessingStatus.EXCEPTION]
    failed = [r for r in results if r.status == ProcessingStatus.FAILED]

    _write_digest(digest_path, clean, flagged, failed)
    _write_exceptions(exceptions_path, flagged, failed)
    _write_import_csv(csv_path, clean)
    _write_run_log(run_log_path, results)

    return digest_path, exceptions_path, csv_path


def _write_run_log(path: Path, results: list[ProcessingResult]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for r in results:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_file": r.source_file,
                "status": r.status.value,
                "vendor_name": r.invoice.vendor_name if r.invoice else None,
                "invoice_number": r.invoice.invoice_number if r.invoice else None,
                "total": r.invoice.total if r.invoice else None,
                "match_status": r.match_result.status.value if r.match_result else None,
                "exception_reason_codes": [e.reason_code for e in r.exceptions],
                "extract_usage": r.extract_usage,
                "code_usage": r.code_usage,
                "errors": r.errors,
            }
            f.write(json.dumps(entry) + "\n")


def _write_digest(path: Path, clean: list[ProcessingResult], flagged: list[ProcessingResult], failed: list[ProcessingResult]) -> None:
    total = len(clean) + len(flagged) + len(failed)
    needs_attention = len(flagged) + len(failed)
    lines = [
        f"# AP Digest - {date.today().isoformat()}",
        "",
        f"**{total} invoice(s) processed - {len(clean)} ready to pay, {needs_attention} need your attention.**",
        "",
    ]
    if clean:
        lines.append("## Ready to pay (see import_ready.csv)")
        for r in clean:
            inv = r.invoice
            lines.append(f"- {_invoice_ref(r)} - ${inv.total:,.2f}, approver: {r.routing.approver_name}")
        lines.append("")
    if flagged or failed:
        lines.append(f"## Needs your attention ({needs_attention}) - see exceptions.md for details")
        for r in flagged:
            reasons = ", ".join(e.reason_code for e in r.exceptions)
            lines.append(f"- {_invoice_ref(r)}: {reasons}")
        for r in failed:
            lines.append(f"- {r.source_file}: could not process ({'; '.join(r.errors)})")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_exceptions(path: Path, flagged: list[ProcessingResult], failed: list[ProcessingResult]) -> None:
    lines = [f"# Exceptions - {date.today().isoformat()}", ""]
    if not flagged and not failed:
        lines.append("No exceptions in this run.")
    for r in flagged:
        lines.append(f"## {_invoice_ref(r)}")
        for e in r.exceptions:
            lines.append(f"- **[{e.severity.value.upper()}] {e.reason_code}**: {e.explanation}")
            lines.append(f"  - Suggested action: {e.suggested_action}")
        lines.append("")
    for r in failed:
        lines.append(f"## {r.source_file}")
        lines.append(f"- **[HIGH] COULD_NOT_PROCESS**: {'; '.join(r.errors)}")
        lines.append("  - Suggested action: Check the file opens correctly and re-save/re-scan it, then drop it back in the inbox.")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_import_csv(path: Path, clean: list[ProcessingResult]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Account", "Debit", "Credit", "Description", "Name"])
        for r in clean:
            inv = r.invoice
            for coding in r.gl_codings:
                line_item = inv.line_items[coding.line_item_index]
                writer.writerow(
                    [
                        inv.invoice_date or "",
                        coding.gl_account_name,
                        f"{line_item.amount:.2f}",
                        "",
                        f"{line_item.description} (Invoice {inv.invoice_number})",
                        inv.vendor_name,
                    ]
                )
            writer.writerow(
                [
                    inv.invoice_date or "",
                    "Accounts Payable",
                    "",
                    f"{inv.total:.2f}",
                    f"Invoice {inv.invoice_number}",
                    inv.vendor_name,
                ]
            )
