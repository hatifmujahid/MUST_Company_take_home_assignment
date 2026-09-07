from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _normalize(s: str) -> str:
    return "".join(ch for ch in s.strip().lower() if ch.isalnum())


def _ledger_path(state_dir: Path) -> Path:
    return state_dir / "ledger.jsonl"


def load_ledger(state_dir: Path) -> list[dict]:
    path = _ledger_path(state_dir)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def is_duplicate(state_dir: Path, content_hash: str, vendor_name: str, invoice_number: str) -> bool:
    key = (_normalize(vendor_name), _normalize(invoice_number))
    for entry in load_ledger(state_dir):
        if entry.get("content_hash") == content_hash:
            return True
        if (_normalize(entry.get("vendor_name", "")), _normalize(entry.get("invoice_number", ""))) == key:
            return True
    return False


def record_processed(state_dir: Path, *, content_hash: str, vendor_name: str, invoice_number: str, source_file: str, status: str) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash,
        "vendor_name": vendor_name,
        "invoice_number": invoice_number,
        "source_file": source_file,
        "status": status,
    }
    with open(_ledger_path(state_dir), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
