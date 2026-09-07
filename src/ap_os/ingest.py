from __future__ import annotations

import email
import hashlib
from pathlib import Path

import pdfplumber


class IngestError(ValueError):
    """Raised when a file's content can't be read at all (e.g. corrupted PDF)."""


def content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            return _extract_pdf_text(path)
        if suffix == ".eml":
            return _extract_eml_text(path)
        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="strict")
        raise IngestError(f"Unsupported file type: {suffix}")
    except IngestError:
        raise
    except Exception as exc:  # noqa: BLE001 - any parser failure becomes an IngestError
        raise IngestError(f"Could not read {path.name}: {exc}") from exc


def _extract_pdf_text(path: Path) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    text = "\n".join(text_parts).strip()
    if not text:
        raise IngestError(f"No extractable text found in {path.name} (possibly a scanned image)")
    return text


def _extract_eml_text(path: Path) -> str:
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f)
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                parts.append(part.get_payload(decode=True).decode(errors="replace"))
        text = "\n".join(parts)
    else:
        text = msg.get_payload(decode=True).decode(errors="replace")
    if not text.strip():
        raise IngestError(f"No text body found in {path.name}")
    return text
