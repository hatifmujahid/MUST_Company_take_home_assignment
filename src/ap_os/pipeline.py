from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import anthropic

from . import code as code_mod
from . import ingest, ledger, match, report, route
from .config import Config
from .exceptions import build_exceptions
from .extract import extract_invoice
from .schemas import Invoice, ProcessingResult, ProcessingStatus
from .validate_reference_data import ReferenceDataError, validate_all

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".eml"}


def process_invoice_file(
    path: Path,
    client: anthropic.Anthropic,
    cfg: Config,
    pos: dict,
    receipts: dict,
    approvers: list,
    chart_of_accounts: list[dict],
) -> ProcessingResult:
    content_hash = ingest.content_hash(path)

    try:
        raw_text = ingest.extract_text(path)
    except ingest.IngestError as exc:
        return ProcessingResult(source_file=path.name, status=ProcessingStatus.FAILED, errors=[str(exc)])

    try:
        extracted, extract_usage = extract_invoice(client, cfg.model, raw_text)
    except Exception as exc:  # noqa: BLE001
        return ProcessingResult(source_file=path.name, status=ProcessingStatus.FAILED, errors=[f"Extraction failed: {exc}"])

    invoice = Invoice(**extracted.model_dump(), source_file=path.name, content_hash=content_hash)

    is_dup = ledger.is_duplicate(cfg.paths.state, content_hash, invoice.vendor_name, invoice.invoice_number)
    match_result = match.match_invoice(
        invoice, pos, receipts, is_dup, cfg.match_tolerance_pct, cfg.match_tolerance_abs
    )

    try:
        gl_codings, code_usage = code_mod.code_invoice(client, cfg.model, invoice, chart_of_accounts)
    except Exception as exc:  # noqa: BLE001
        return ProcessingResult(
            source_file=path.name,
            status=ProcessingStatus.FAILED,
            invoice=invoice,
            match_result=match_result,
            extract_usage=extract_usage,
            errors=[f"GL coding failed: {exc}"],
        )

    routing, over_threshold = route.route_invoice(invoice.total, approvers)
    exceptions = build_exceptions(invoice, match_result, gl_codings, cfg.confidence_threshold, over_threshold)

    status = ProcessingStatus.EXCEPTION if exceptions else ProcessingStatus.CLEAN

    ledger.record_processed(
        cfg.paths.state,
        content_hash=content_hash,
        vendor_name=invoice.vendor_name,
        invoice_number=invoice.invoice_number,
        source_file=path.name,
        status=status.value,
    )

    return ProcessingResult(
        source_file=path.name,
        status=status,
        invoice=invoice,
        match_result=match_result,
        gl_codings=gl_codings,
        routing=routing,
        exceptions=exceptions,
        extract_usage=extract_usage,
        code_usage=code_usage,
    )


def run_pipeline(cfg: Config, dry_run: bool = False) -> list[ProcessingResult]:
    try:
        validate_all(cfg.paths.data)
    except ReferenceDataError as exc:
        raise SystemExit(f"Reference data problem, nothing was processed: {exc}") from exc

    files = sorted(p for p in cfg.paths.inbox.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)
    if not files:
        return []

    if dry_run:
        return [ProcessingResult(source_file=p.name, status=ProcessingStatus.CLEAN) for p in files]

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    pos = match.load_pos(cfg.paths.data)
    receipts = match.load_receipts(cfg.paths.data)
    approvers = route.load_approvers(cfg.paths.data)
    chart_of_accounts = code_mod.load_chart_of_accounts(cfg.paths.data)

    results: list[ProcessingResult] = []
    for path in files:
        result = process_invoice_file(path, client, cfg, pos, receipts, approvers, chart_of_accounts)
        results.append(result)

        dest_dir = cfg.paths.processed / date.today().isoformat()
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest_dir / path.name))

    report.write_reports(results, cfg.paths.output)
    return results
