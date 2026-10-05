"""Shared state passed between invoice workflow graph nodes."""

from typing import Any, TypedDict


class InvoiceState(TypedDict, total=False):
    # Input and identity
    file_path: str
    file_hash: str
    # Plain text pulled from the source document. TODO: replace with real
    # PDF/OCR extraction; for now callers pass this in directly.
    document_text: str
    invoice_id: int | str | None
    is_invoice: bool
    duplicate: bool

    # Extracted invoice fields, shaped like app.graph.schemas.ExtractedInvoice.
    invoice_fields: dict[str, Any]
    validation_errors: list[str]
    retry_count: int
    max_retries: int

    # Matching, policy, and routing outputs
    match_result: dict[str, Any]
    policy_result: dict[str, Any]
    route: str
    status: str
    reviewer_decision: str | None
    posted: bool
    audit_events: list[str]
    error: str | None
