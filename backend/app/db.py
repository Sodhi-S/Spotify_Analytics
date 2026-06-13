from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(settings.db_connection_string, pool_pre_ping=True, future=True)


@contextmanager
def db_connection() -> Iterator[Connection]:
    with get_engine().begin() as connection:
        yield connection


def qualified_table(table_name: str) -> str:
    schema = get_settings().warehouse_schema.strip()
    return f"{schema}.{table_name}" if schema else table_name
