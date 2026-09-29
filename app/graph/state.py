"""Shared state passed between invoice workflow graph nodes."""

from typing import Any, TypedDict


class InvoiceState(TypedDict, total=False):
    # Input and identity
    file_path: str
    file_hash: str
    invoice_id: int | str | None
    is_invoice: bool
    duplicate: bool

    # Extracted invoice fields. TODO: replace the loose mapping with a validated
    # Pydantic Invoice model once the extraction schema is implemented.
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
