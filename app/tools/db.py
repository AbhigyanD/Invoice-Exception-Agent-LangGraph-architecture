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

"""Iterator is a generic type from the typing module that represents 
an iterator object. In this context, it indicates that the get_conn function will 
yield a psycopg.Connection object, which can be used to interact with the PostgreSQL database."""

"""get_conn is the context manager function that establishes a connection to the PostgreSQL database using the psycopg library."""