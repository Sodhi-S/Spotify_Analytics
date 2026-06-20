from __future__ import annotations

import base64
import binascii
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import get_settings

LEGACY_USER_ID = "legacy-single-user"
PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 16


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    lastfm_username: str
    display_name: str | None = None
    has_password: bool = False


def normalize_lastfm_username(username: str) -> str:
    cleaned = username.strip()
    if not cleaned:
        raise ValueError("Last.fm username is required")
    return cleaned.lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _encode_base64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decode_base64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if len(password) > 128:
        raise ValueError("Password must be 128 characters or fewer.")


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "$".join(
        [
            PASSWORD_ALGORITHM,
            str(PASSWORD_ITERATIONS),
            _encode_base64(salt),
            _encode_base64(digest),
        ]
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = _decode_base64(salt_text)
        expected = _decode_base64(digest_text)
    except (ValueError, binascii.Error):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return secrets.compare_digest(actual, expected)


def _user_from_row(row: Any) -> AuthenticatedUser:
    mapping = dict(row._mapping)
    mapping["has_password"] = bool(mapping.pop("password_hash", None))
    return AuthenticatedUser(**mapping)


def new_token() -> str:
    return secrets.token_urlsafe(48)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def get_or_create_user(
    connection: Connection,
    lastfm_username: str,
    display_name: str | None = None,
) -> AuthenticatedUser:
    username = normalize_lastfm_username(lastfm_username)
    row = connection.execute(
        text(
            """
            insert into app.users (
                id, lastfm_username, display_name, created_at, updated_at, last_login_at
            )
            values (
                :id, :lastfm_username, :display_name,
                current_timestamp, current_timestamp, current_timestamp
            )
            on conflict (lastfm_username) do update set
                display_name = coalesce(excluded.display_name, app.users.display_name),
                updated_at = current_timestamp,
                last_login_at = current_timestamp
            returning id, lastfm_username, display_name, password_hash
            """
        ),
        {
            "id": new_id("user"),
            "lastfm_username": username,
            "display_name": display_name or lastfm_username.strip(),
        },
    ).one()
    user = _user_from_row(row)
    configured_username = get_settings().lastfm_username.strip()
    if configured_username and normalize_lastfm_username(configured_username) == username:
        claim_legacy_single_user_data(connection, user.id)
    return user


def get_user(connection: Connection, user_id: str) -> AuthenticatedUser | None:
    row = connection.execute(
        text(
            """
            select id, lastfm_username, display_name, password_hash
            from app.users
            where id = :user_id
            """
        ),
        {"user_id": user_id},
    ).first()
    return _user_from_row(row) if row else None


def authenticate_with_password(
    connection: Connection,
    lastfm_username: str,
    password: str,
) -> AuthenticatedUser | None:
    username = normalize_lastfm_username(lastfm_username)
    row = connection.execute(
        text(
            """
            select id, lastfm_username, display_name, password_hash
            from app.users
            where lastfm_username = :lastfm_username
            """
        ),
        {"lastfm_username": username},
    ).first()
    if row is None or not verify_password(password, row._mapping["password_hash"]):
        return None

    connection.execute(
        text(
            """
            update app.users
            set last_login_at = current_timestamp,
                updated_at = current_timestamp
            where id = :user_id
            """
        ),
        {"user_id": row._mapping["id"]},
    )
    return _user_from_row(row)


def set_user_password(connection: Connection, user_id: str, password: str) -> AuthenticatedUser:
    password_hash = hash_password(password)
    row = connection.execute(
        text(
            """
            update app.users
            set password_hash = :password_hash,
                password_updated_at = current_timestamp,
                updated_at = current_timestamp
            where id = :user_id
            returning id, lastfm_username, display_name, password_hash
            """
        ),
        {"user_id": user_id, "password_hash": password_hash},
    ).one()
    return _user_from_row(row)


def ensure_configured_user(connection: Connection) -> AuthenticatedUser | None:
    settings = get_settings()
    if not settings.lastfm_username.strip():
        return None
    user = get_or_create_user(
        connection,
        settings.lastfm_username,
        display_name=settings.lastfm_username,
    )
    claim_legacy_single_user_data(connection, user.id)
    return user


def claim_legacy_single_user_data(connection: Connection, user_id: str) -> None:
    if user_id == LEGACY_USER_ID:
        return

    connection.execute(
        text(
            """
            delete from raw.recent_tracks legacy
            using raw.recent_tracks target
            where legacy.user_id = :legacy_user_id
              and target.user_id = :user_id
              and target.played_at = legacy.played_at
              and target.track_name = legacy.track_name
              and target.artist_name = legacy.artist_name
            """
        ),
        {"legacy_user_id": LEGACY_USER_ID, "user_id": user_id},
    )
    for table_name in ("recent_tracks", "top_artists", "top_tracks", "raw_failed"):
        connection.execute(
            text(
                f"""
                update raw.{table_name}
                set user_id = :user_id
                where user_id = :legacy_user_id
                """
            ),
            {"legacy_user_id": LEGACY_USER_ID, "user_id": user_id},
        )
    connection.execute(
        text(
            """
            insert into app.user_settings (user_id, key, value, updated_at)
            select :user_id, key, value, updated_at
            from app.user_settings
            where user_id = :legacy_user_id
            on conflict (user_id, key) do nothing
            """
        ),
        {"legacy_user_id": LEGACY_USER_ID, "user_id": user_id},
    )
    connection.execute(
        text(
            """
            delete from app.user_ingestion_state legacy
            using app.user_ingestion_state target
            where legacy.user_id = :legacy_user_id
              and target.user_id = :user_id
              and target.source = legacy.source
            """
        ),
        {"legacy_user_id": LEGACY_USER_ID, "user_id": user_id},
    )
    connection.execute(
        text(
            """
            update app.user_ingestion_state
            set user_id = :user_id
            where user_id = :legacy_user_id
            """
        ),
        {"legacy_user_id": LEGACY_USER_ID, "user_id": user_id},
    )


def create_session(connection: Connection, user_id: str) -> tuple[str, datetime]:
    token = new_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=get_settings().app_session_days)
    connection.execute(
        text(
            """
            insert into app.auth_sessions (
                session_token_hash, user_id, created_at, expires_at
            )
            values (:session_token_hash, :user_id, current_timestamp, :expires_at)
            """
        ),
        {
            "session_token_hash": _hash_token(token),
            "user_id": user_id,
            "expires_at": expires_at,
        },
    )
    return token, expires_at


def revoke_session(connection: Connection, token: str) -> None:
    connection.execute(
        text(
            """
            update app.auth_sessions
            set revoked_at = current_timestamp
            where session_token_hash = :session_token_hash
            """
        ),
        {"session_token_hash": _hash_token(token)},
    )


def user_for_session(connection: Connection, token: str | None) -> AuthenticatedUser | None:
    if not token:
        return None
    row = connection.execute(
        text(
            """
            select users.id, users.lastfm_username, users.display_name, users.password_hash
            from app.auth_sessions sessions
            join app.users users on sessions.user_id = users.id
            where sessions.session_token_hash = :session_token_hash
              and sessions.revoked_at is null
              and sessions.expires_at > current_timestamp
            """
        ),
        {"session_token_hash": _hash_token(token)},
    ).first()
    return _user_from_row(row) if row else None


def create_ingestion_job(
    connection: Connection,
    user_id: str,
    job_type: str = "lastfm_initial_import",
) -> str:
    job_id = new_id("job")
    connection.execute(
        text(
            """
            insert into app.ingestion_jobs (id, user_id, job_type, status, created_at)
            values (:id, :user_id, :job_type, 'queued', current_timestamp)
            """
        ),
        {"id": job_id, "user_id": user_id, "job_type": job_type},
    )
    return job_id


def update_ingestion_job(
    connection: Connection,
    job_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    connection.execute(
        text(
            """
            update app.ingestion_jobs
            set
                status = :status,
                started_at = case
                    when :status = 'running' and started_at is null then current_timestamp
                    else started_at
                end,
                completed_at = case
                    when :status in ('succeeded', 'failed') then current_timestamp
                    else completed_at
                end,
                result = cast(:result as jsonb),
                error_message = :error_message
            where id = :job_id
            """
        ),
        {
            "job_id": job_id,
            "status": status,
            "result": json.dumps(result or {}),
            "error_message": error_message[:1000] if error_message else None,
        },
    )


def latest_ingestion_job(connection: Connection, user_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        text(
            """
            select id, job_type, status, result, error_message, created_at, started_at, completed_at
            from app.ingestion_jobs
            where user_id = :user_id
            order by created_at desc
            limit 1
            """
        ),
        {"user_id": user_id},
    ).first()
    if row is None:
        return None

    item = dict(row._mapping)
    for key in ("created_at", "started_at", "completed_at"):
        value = item[key]
        item[key] = value.isoformat() if value is not None else None
    return item
