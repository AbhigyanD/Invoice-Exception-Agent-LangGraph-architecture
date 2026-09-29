"""Three-way match: invoice lines against a vendor's open POs and goods receipts."""

from decimal import Decimal

from app.tools.db import get_conn


def find_vendor_id(vendor_name: str) -> int | None:
    normalized = (vendor_name or "").strip().lower()
    if not normalized:
        return None
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM vendor WHERE normalized_name = %s", (normalized,))
        row = cur.fetchone()
        return row["id"] if row else None


def three_way_match(vendor_id: int, lines: list[dict]) -> dict:
    """Compare each invoice line's quantity against the matching PO's ordered
    and received quantities. Matches on vendor + item name."""
    mismatches: list[str] = []

    with get_conn() as conn, conn.cursor() as cur:
        for line in lines:
            item = line.get("item", "")
            invoiced_qty = Decimal(str(line.get("qty", 0)))

            cur.execute(
                """
                SELECT p.id, p.qty AS ordered_qty,
                       COALESCE(SUM(g.qty), 0) AS received_qty
                FROM po p
                LEFT JOIN goods_receipt g ON g.po_id = p.id
                WHERE p.vendor_id = %s AND lower(p.item) = lower(%s)
                GROUP BY p.id, p.qty
                ORDER BY p.id
                LIMIT 1
                """,
                (vendor_id, item),
            )
            po = cur.fetchone()

            if po is None:
                mismatches.append(f"no PO found for line item '{item}'")
                continue
            if invoiced_qty > po["ordered_qty"]:
                mismatches.append(
                    f"'{item}': invoiced qty {invoiced_qty} exceeds ordered qty {po['ordered_qty']}"
                )
            if invoiced_qty > po["received_qty"]:
                mismatches.append(
                    f"'{item}': invoiced qty {invoiced_qty} exceeds received qty {po['received_qty']}"
                )

    return {"matched": not mismatches, "mismatches": mismatches}
