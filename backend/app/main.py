from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.schemas import OverviewResponse
from app.core.config import get_settings
from app.db import db_connection
from app.services.overview import VALID_PERIODS, OverviewService

logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(title="Music Listening Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/stats/overview", response_model=OverviewResponse)
def get_overview(
    period: str = Query(
        default="all",
        description="Accepted values: 7d, 30d, 6m, all",
    )
) -> OverviewResponse:
    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=400,
            detail="Invalid period. Accepted values: 7d, 30d, 6m, all",
        )

    try:
        with db_connection() as connection:
            return OverviewService(connection).get_overview(period)
    except SQLAlchemyError:
        logger.exception("Database error while loading overview")
        raise HTTPException(status_code=500, detail="Internal server error") from None
