"""Append-only audit trail, written on every exit path."""

import json

from app.tools.db import get_conn


def write_audit_event(invoice_id: int | None, event: str, detail: dict | None = None) -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO audit_log (invoice_id, event, detail) VALUES (%s, %s, %s)",
            (invoice_id, event, json.dumps(detail or {})),
        )
