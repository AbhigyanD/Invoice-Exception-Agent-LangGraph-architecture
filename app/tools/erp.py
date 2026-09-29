"""Idempotent ERP poster: writes an idempotency key once per invoice."""

from app.tools.db import get_conn


def post_invoice(invoice_id: int) -> None:
    idempotency_key = f"invoice-{invoice_id}"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO erp_posted (invoice_id, idempotency_key)
            VALUES (%s, %s)
            ON CONFLICT (invoice_id) DO NOTHING
            """,
            (invoice_id, idempotency_key),
        )
        cur.execute(
            "UPDATE invoice SET status = 'posted', updated_at = now() WHERE id = %s",
            (invoice_id,),
        )
