"""Insert a small, repeatable set of sample vendors, POs, and receipts for testing.

Run from the repository root with ``python -m app.db.seed`` after applying
``app/db/schema.sql``. The script is safe to run more than once.
"""

from decimal import Decimal

import psycopg

from app.config import settings


VENDORS = (
    {
        "name": "Northstar Office Supply",
        "normalized_name": "northstar office supply",
        "tax_id": "NS-10001",
        "email": "ap@northstar.example",
        "orders": (
            ("Copy paper, A4", Decimal("6.50"), Decimal("100"), Decimal("100")),
            ("Ballpoint pens, blue", Decimal("0.75"), Decimal("200"), Decimal("180")),
        ),
    },
    {
        "name": "Acme Industrial Parts",
        "normalized_name": "acme industrial parts",
        "tax_id": "AC-20450",
        "email": "billing@acme-parts.example",
        "orders": (
            ("Hex bolt M8", Decimal("0.40"), Decimal("500"), Decimal("500")),
            ("Safety gloves, size L", Decimal("12.00"), Decimal("40"), Decimal("40")),
        ),
    },
    {
        "name": "Greenfield Catering",
        "normalized_name": "greenfield catering",
        "tax_id": "GF-30990",
        "email": "invoices@greenfield.example",
        "orders": (
            ("Coffee beans, 1 kg", Decimal("18.00"), Decimal("25"), Decimal("20")),
            ("Paper cups, 12 oz", Decimal("0.08"), Decimal("1000"), Decimal("1000")),
        ),
    },
)


def seed() -> int:
    inserted_orders = 0
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            for vendor_data in VENDORS:
                cur.execute(
                    """
                    INSERT INTO vendor (name, normalized_name, tax_id, email)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (normalized_name) DO UPDATE SET
                        name = EXCLUDED.name,
                        tax_id = EXCLUDED.tax_id,
                        email = EXCLUDED.email
                    RETURNING id
                    """,
                    (
                        vendor_data["name"],
                        vendor_data["normalized_name"],
                        vendor_data["tax_id"],
                        vendor_data["email"],
                    ),
                )
                vendor_id = cur.fetchone()[0]

                for item, amount, ordered_qty, received_qty in vendor_data["orders"]:
                    cur.execute(
                        """
                        SELECT id FROM po
                        WHERE vendor_id = %s AND item = %s AND amount = %s AND qty = %s
                        ORDER BY id LIMIT 1
                        """,
                        (vendor_id, item, amount, ordered_qty),
                    )
                    row = cur.fetchone()
                    if row:
                        po_id = row[0]
                    else:
                        cur.execute(
                            """
                            INSERT INTO po (vendor_id, item, amount, qty, status)
                            VALUES (%s, %s, %s, %s, 'open')
                            RETURNING id
                            """,
                            (vendor_id, item, amount, ordered_qty),
                        )
                        po_id = cur.fetchone()[0]
                        inserted_orders += 1

                    cur.execute(
                        """
                        SELECT 1 FROM goods_receipt
                        WHERE po_id = %s AND qty = %s
                        LIMIT 1
                        """,
                        (po_id, received_qty),
                    )
                    if cur.fetchone() is None:
                        cur.execute(
                            """
                            INSERT INTO goods_receipt (po_id, qty)
                            VALUES (%s, %s)
                            """,
                            (po_id, received_qty),
                        )

    return inserted_orders


if __name__ == "__main__":
    count = seed()
    print(f"Sample data ready. Added {count} purchase order(s).")
