"""Build the invoice workflow graph with deterministic placeholder nodes."""

from decimal import Decimal
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.graph.state import InvoiceState
from app.tools.audit import write_audit_event
from app.tools.erp import post_invoice
from app.tools.ingest import find_or_create_invoice, hash_file
from app.tools.match import find_vendor_id, three_way_match
from app.tools.policy import evaluate_policy
from app.tools.db import get_conn


def ingest_node(state: InvoiceState) -> dict:
    """Store the upload, hash it, and stop exact duplicates before extraction."""
    file_hash = hash_file(state.get("file_path"), state.get("file_hash"))
    invoice_id, duplicate = find_or_create_invoice(file_hash)
    print(f"ingest_node: file_hash={file_hash} invoice_id={invoice_id} duplicate={duplicate}")
    return {
        "file_hash": file_hash,
        "invoice_id": invoice_id,
        "duplicate": duplicate,
        "status": "duplicate" if duplicate else "ingested",
    }


def classify_node(state: InvoiceState) -> dict:
    """Placeholder document classifier."""
    # TODO: classify the document using its content and route non-invoices to reject.
    print(f"classify_node: classifying document {state.get('file_path')}")
    return {"is_invoice": True}


def extract_node(state: InvoiceState) -> dict:
    """Return fixed invoice fields; second pass simulates a repaired extraction."""
    # TODO: extract vendor, PO, line items, totals, dates, and confidence into a schema.
    print(f"extract_node: extracting fields for document {state.get('file_path')}")

    fields = {
        "vendor_name": "Northstar Office Supply",
        "po_number": "PO-STUB-001",
        "currency": "CAD",
        "subtotal": 650.00 if state.get("retry_count", 0) else 649.00,
        "total_amount": 650.00,
        "lines": [{"item": "Copy paper, A4", "qty": 100, "unit_price": 6.50}],
        "confidence": 0.98,
    }
    print(f"extract_node: extracted fields for document {state.get('file_path')}: {fields}")
    return {"invoice_fields": fields}


def validate_node(state: InvoiceState) -> dict:
    """Check required fields, line-item arithmetic, and extraction confidence."""
    fields = state.get("invoice_fields", {})
    errors: list[str] = []

    for key in ("vendor_name", "total_amount", "currency", "lines"):
        if not fields.get(key):
            errors.append(f"missing required field '{key}'")

    lines = fields.get("lines", [])
    computed_subtotal = sum(
        (Decimal(str(line.get("qty", 0))) * Decimal(str(line.get("unit_price", 0))) for line in lines),
        Decimal("0"),
    )
    subtotal = fields.get("subtotal")
    if subtotal is not None and abs(Decimal(str(subtotal)) - computed_subtotal) > Decimal("0.01"):
        errors.append(f"subtotal {subtotal} does not match sum of line items {computed_subtotal}")

    total_amount = fields.get("total_amount")
    if (
        subtotal is not None
        and total_amount is not None
        and abs(Decimal(str(subtotal)) - Decimal(str(total_amount))) > Decimal("0.01")
    ):
        errors.append(f"subtotal {subtotal} does not match total_amount {total_amount}")

    confidence = fields.get("confidence")
    if confidence is not None and confidence < settings.min_confidence:
        errors.append(f"extraction confidence {confidence} below minimum {settings.min_confidence}")

    return {"validation_errors": errors}


def repair_node(state: InvoiceState) -> dict:
    """Placeholder repair step; the following extract pass uses the retry count."""
    # TODO: feed validation errors and original evidence to a bounded repair prompt.
    return {"retry_count": state.get("retry_count", 0) + 1}


def match_node(state: InvoiceState) -> dict:
    """Compare invoice lines against the vendor's open POs and received quantities."""
    fields = state.get("invoice_fields", {})
    vendor_name = fields.get("vendor_name", "")
    vendor_id = find_vendor_id(vendor_name)
    if vendor_id is None:
        return {"match_result": {"matched": False, "mismatches": [f"unknown vendor '{vendor_name}'"]}}
    return {"match_result": three_way_match(vendor_id, fields.get("lines", []))}


def policy_node(state: InvoiceState) -> dict:
    """Apply the two hard AP limits: max auto-approve amount and min confidence."""
    fields = state.get("invoice_fields", {})
    return {
        "policy_result": evaluate_policy(
            fields.get("total_amount"),
            fields.get("confidence"),
        )
    }


def route_node(state: InvoiceState) -> dict:
    """Choose post, review, or exception using the match and policy evidence."""
    if not state.get("match_result", {}).get("matched"):
        return {"route": "exception"}
    if state.get("policy_result", {}).get("risk") == "high":
        return {"route": "review"}
    return {"route": "post"}


def exception_node(state: InvoiceState) -> dict:
    # TODO: coordinate exception workers and create a reviewer-ready explanation.
    return {"status": "pending_review"}


def review_node(state: InvoiceState) -> dict:
    # TODO: use LangGraph interrupt() and persist the review task before waiting.
    decision = state.get("reviewer_decision", "approved")
    return {"reviewer_decision": decision, "status": decision}


def post_node(state: InvoiceState) -> dict:
    """Post to the ERP table with a stable idempotency key."""
    invoice_id = state.get("invoice_id")
    if invoice_id is not None:
        post_invoice(invoice_id)
    return {"posted": True, "status": "posted"}


def reject_node(state: InvoiceState) -> dict:
    """Persist the rejection reason against the invoice row.

    A duplicate hit points at an invoice that already went through the
    pipeline once, so it must not overwrite that invoice's real status
    (e.g. 'posted') -- only a genuinely new, rejected invoice gets marked.
    """
    invoice_id = state.get("invoice_id")
    duplicate = state.get("duplicate", False)
    reason = "duplicate invoice" if duplicate else "not an invoice"
    if invoice_id is not None and not duplicate:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE invoice SET status = 'rejected', updated_at = now() WHERE id = %s",
                (invoice_id,),
            )
    return {"status": "duplicate" if duplicate else "rejected", "error": reason}


def audit_node(state: InvoiceState) -> dict:
    """Write the terminal event, with supporting evidence, to audit_log."""
    status = state.get("status", "completed")
    event = f"workflow_{status}"
    write_audit_event(
        state.get("invoice_id"),
        event,
        {
            "route": state.get("route"),
            "match_result": state.get("match_result"),
            "policy_result": state.get("policy_result"),
            "validation_errors": state.get("validation_errors"),
        },
    )
    return {"audit_events": [*state.get("audit_events", []), event]}


def _after_ingest(state: InvoiceState) -> Literal["classify", "reject"]:
    return "reject" if state.get("duplicate") else "classify"


def _after_classify(state: InvoiceState) -> Literal["extract", "reject"]:
    return "extract" if state.get("is_invoice") else "reject"


def _after_validate(state: InvoiceState) -> Literal["repair", "match", "exception"]:
    if not state.get("validation_errors"):
        return "match"
    if state.get("retry_count", 0) < state.get("max_retries", 2):
        return "repair"
    return "exception"


def _after_route(state: InvoiceState) -> Literal["post", "review", "exception", "reject"]:
    route = state.get("route", "review")
    return route if route in {"post", "review", "exception", "reject"} else "review"


def _after_review(state: InvoiceState) -> Literal["post", "reject", "validate"]:
    decision = state.get("reviewer_decision")
    if decision == "approved":
        return "post"
    if decision == "rejected":
        return "reject"
    # TODO: apply reviewer edits to invoice_fields before revalidation.
    return "validate"


def build_graph():
    """Create and compile the stub invoice workflow."""
    graph = StateGraph(InvoiceState)

    graph.add_node("ingest", ingest_node)
    graph.add_node("classify", classify_node)
    graph.add_node("extract", extract_node)
    graph.add_node("validate", validate_node)
    graph.add_node("repair", repair_node)
    graph.add_node("match", match_node)
    graph.add_node("policy", policy_node)
    graph.add_node("route", route_node)
    graph.add_node("exception", exception_node)
    graph.add_node("review", review_node)
    graph.add_node("post", post_node)
    graph.add_node("reject", reject_node)
    graph.add_node("audit", audit_node)

    graph.add_edge(START, "ingest")
    graph.add_conditional_edges("ingest", _after_ingest)
    graph.add_conditional_edges("classify", _after_classify)
    graph.add_edge("extract", "validate")
    graph.add_conditional_edges("validate", _after_validate)
    graph.add_edge("repair", "extract")
    graph.add_edge("match", "policy")
    graph.add_edge("policy", "route")
    graph.add_conditional_edges("route", _after_route)
    graph.add_edge("exception", "review")
    graph.add_conditional_edges("review", _after_review)
    graph.add_edge("post", "audit")
    graph.add_edge("reject", "audit")
    graph.add_edge("audit", END)

    return graph.compile()


if __name__ == "__main__":
    # TODO: replace this demo input with a real upload/API invocation.
    result = build_graph().invoke(
        {"file_path": "sample-invoice.pdf", "retry_count": 0, "max_retries": 2, "audit_events": []}
    )
    print(result)
