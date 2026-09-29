"""File hashing and dedupe/insert against the invoice table."""

import hashlib
from pathlib import Path

from app.tools.db import get_conn


def hash_file(file_path: str | None, file_hash: str | None = None) -> str:
    """Return a content hash, falling back to hashing the path for demo runs
    where no real file is on disk."""
    if file_hash:
        return file_hash
    if file_path and Path(file_path).exists():
        return hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
    return hashlib.sha256((file_path or "unknown").encode()).hexdigest()


def find_or_create_invoice(file_hash: str) -> tuple[int, bool]:
    """Look up an invoice by content hash, or create a new row.

    Returns (invoice_id, is_duplicate).
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM invoice WHERE file_hash = %s", (file_hash,))
        row = cur.fetchone()
        if row:
            return row["id"], True

        cur.execute(
            "INSERT INTO invoice (file_hash, status) VALUES (%s, 'received') RETURNING id",
            (file_hash,),
        )
        return cur.fetchone()["id"], False
