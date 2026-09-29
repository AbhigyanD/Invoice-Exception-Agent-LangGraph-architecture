"""Build the invoice workflow graph with deterministic placeholder nodes."""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.graph.state import InvoiceState


def ingest_node(state: InvoiceState) -> dict:
    """Placeholder for storing the upload, hashing it, and checking duplicates."""
    # TODO: persist the source file and invoice row; compute a content hash and
    # stop duplicate files before sending them through extraction.
    return {"file_hash": state.get("file_hash", "stub-file-hash"), "status": "ingested"}


def classify_node(state: InvoiceState) -> dict:
    """Placeholder document classifier."""
    # TODO: classify the document using its content and route non-invoices to reject.
    return {"is_invoice": True}


def extract_node(state: InvoiceState) -> dict:
    """Return fixed invoice fields; second pass simulates a repaired extraction."""
    # TODO: extract vendor, PO, line items, totals, dates, and confidence into a schema.
    fields = {
        "vendor_name": "Northstar Office Supply",
        "po_number": "PO-STUB-001",
        "currency": "CAD",
        "subtotal": 650.00 if state.get("retry_count", 0) else 649.00,
        "total_amount": 650.00,
        "lines": [{"item": "Copy paper, A4", "qty": 100, "unit_price": 6.50}],
        "confidence": 0.98,
    }
    return {"invoice_fields": fields}


def validate_node(state: InvoiceState) -> dict:
    """Stub validation that creates one error to demonstrate the repair loop."""
    # TODO: validate arithmetic, required fields, dates, currency, and vendor.
    fields = state.get("invoice_fields", {})
    errors = [] if fields.get("subtotal") == fields.get("total_amount") else ["subtotal does not match total"]
    return {"validation_errors": errors}


def repair_node(state: InvoiceState) -> dict:
    """Placeholder repair step; the following extract pass uses the retry count."""
    # TODO: feed validation errors and original evidence to a bounded repair prompt.
    return {"retry_count": state.get("retry_count", 0) + 1}


def match_node(state: InvoiceState) -> dict:
    # TODO: compare invoice lines against vendor, PO lines, and received quantities in Postgres.
    return {"match_result": {"matched": True, "reason": "stub match"}}


def policy_node(state: InvoiceState) -> dict:
    # TODO: apply deterministic AP policy and any required policy retrieval.
    return {"policy_result": {"allowed": True, "risk": "low"}}


def route_node(state: InvoiceState) -> dict:
    # TODO: choose post, review, exception, or reject using match and policy evidence.
    return {"route": "post" if state.get("match_result", {}).get("matched") else "review"}


def exception_node(state: InvoiceState) -> dict:
    # TODO: coordinate exception workers and create a reviewer-ready explanation.
    return {"status": "pending_review"}


def review_node(state: InvoiceState) -> dict:
    # TODO: use LangGraph interrupt() and persist the review task before waiting.
    decision = state.get("reviewer_decision", "approved")
    return {"reviewer_decision": decision, "status": decision}


def post_node(state: InvoiceState) -> dict:
    # TODO: post to the ERP table with a stable idempotency key.
    return {"posted": True, "status": "posted"}


def reject_node(state: InvoiceState) -> dict:
    # TODO: persist rejection reason and notify the submitting system.
    return {"status": "rejected"}


def audit_node(state: InvoiceState) -> dict:
    # TODO: write each terminal event and its supporting evidence to audit_log.
    status = state.get("status", "completed")
    return {"audit_events": [*state.get("audit_events", []), f"workflow_{status}"]}


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
    graph.add_edge("ingest", "classify")
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
