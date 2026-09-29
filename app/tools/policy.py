"""Deterministic AP policy checks. No retrieval yet -- just the two hard limits
from settings. RAG over a written policy document is a later addition."""

from app.config import settings


def evaluate_policy(total_amount: float | None, confidence: float | None) -> dict:
    reasons: list[str] = []

    if total_amount is None or total_amount > settings.auto_approve_max_amount:
        reasons.append(
            f"amount {total_amount} exceeds auto-approve limit {settings.auto_approve_max_amount}"
        )
    if confidence is None or confidence < settings.min_confidence:
        reasons.append(
            f"extraction confidence {confidence} below minimum {settings.min_confidence}"
        )

    risk = "low" if not reasons else "high"
    return {"allowed": True, "risk": risk, "reasons": reasons}
