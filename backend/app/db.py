from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from .config import Settings


def connect(settings: Settings) -> psycopg.Connection:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required when using CockroachDB storage.")
    conn = psycopg.connect(
        _normalize_database_url(settings.database_url),
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=10,
    )
    register_vector(conn)
    return conn


def execute_sql_file(settings: Settings, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with connect(settings) as conn:
        conn.execute(sql)


def _normalize_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    sslmode = query.get("sslmode", "")
    if sslmode.startswith("verify") and "sslrootcert" not in query:
        default_root_cert = Path(os.environ.get("APPDATA", "")) / "postgresql" / "root.crt"
        if default_root_cert.exists():
            query["sslrootcert"] = str(default_root_cert)
        else:
            query["sslmode"] = "require"
    return urlunparse(parsed._replace(query=urlencode(query)))
