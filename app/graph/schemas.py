"""Structured output schemas for the classify and extract LLM calls."""

from pydantic import BaseModel, Field


class ClassifyResult(BaseModel):
    is_invoice: bool = Field(description="True if the document is a supplier invoice")
    reason: str = Field(description="One sentence explaining the decision")


class InvoiceLine(BaseModel):
    item: str
    qty: float
    unit_price: float


class ExtractedInvoice(BaseModel):
    vendor_name: str
    po_number: str | None = None
    currency: str = Field(description="ISO 4217 currency code, e.g. USD")
    invoice_date: str | None = Field(default=None, description="ISO 8601 date, e.g. 2026-01-15")
    subtotal: float
    total_amount: float
    lines: list[InvoiceLine]
    confidence: float = Field(ge=0, le=1, description="Model's confidence in this extraction")
