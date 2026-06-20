from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db import db_connection
from app.services.auth import AuthenticatedUser, user_for_session

logger = logging.getLogger(__name__)


def get_current_user(request: Request) -> AuthenticatedUser:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        with db_connection() as connection:
            user = user_for_session(connection, token)
    except SQLAlchemyError:
        logger.exception("Database error while loading auth session")
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from None

    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
