from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float


class ExtractedInvoice(BaseModel):
    """Raw extraction result straight from Claude, before any business logic runs."""

    vendor_name: str
    invoice_number: str
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    po_number: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: float
    currency: str = "USD"
    confidence: float = Field(ge=0.0, le=1.0)
    extraction_notes: Optional[str] = None


class Invoice(ExtractedInvoice):
    """Extracted invoice enriched with pipeline bookkeeping fields."""

    source_file: str
    content_hash: str


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    NO_PO_FOUND = "NO_PO_FOUND"
    DUPLICATE = "DUPLICATE"
    OVER_TOLERANCE = "OVER_TOLERANCE"


class MatchResult(BaseModel):
    status: MatchStatus
    po_number: Optional[str] = None
    po_amount: Optional[float] = None
    receipt_amount: Optional[float] = None
    invoice_amount: float
    variance: Optional[float] = None
    detail: str


class GLCoding(BaseModel):
    line_item_index: int
    gl_code: str
    gl_account_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: Optional[str] = None


class RoutingDecision(BaseModel):
    approver_name: str
    approver_email: str
    reason: str


class ExceptionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExceptionRecord(BaseModel):
    reason_code: str
    explanation: str
    suggested_action: str
    severity: ExceptionSeverity


class ProcessingStatus(str, Enum):
    CLEAN = "CLEAN"
    EXCEPTION = "EXCEPTION"
    FAILED = "FAILED"


class ProcessingResult(BaseModel):
    source_file: str
    status: ProcessingStatus
    invoice: Optional[Invoice] = None
    match_result: Optional[MatchResult] = None
    gl_codings: list[GLCoding] = Field(default_factory=list)
    routing: Optional[RoutingDecision] = None
    exceptions: list[ExceptionRecord] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    extract_usage: Optional[dict] = None
    code_usage: Optional[dict] = None
