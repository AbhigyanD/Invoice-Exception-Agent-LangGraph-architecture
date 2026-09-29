"""Shared Postgres connection helper for tool modules."""

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import settings


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn
