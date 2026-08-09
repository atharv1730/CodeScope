"""Health endpoint: reports DB/Redis reachability, queue length, worker count."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.celery_app import celery_app
from app.config import settings
from app.database import engine
from app.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_ok = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_ok = f"error: {exc}"

    redis_ok = "ok"
    queued: int | None = None
    workers: int | None = None
    try:
        import redis  # local import so a redis outage can't break module load

        client = redis.Redis.from_url(settings.redis_url)
        client.ping()
        # Default Celery queue name is "celery"; length approximates backlog.
        queued = int(client.llen("celery"))
    except Exception as exc:  # noqa: BLE001
        redis_ok = f"error: {exc}"

    try:
        pong = celery_app.control.ping(timeout=0.5)
        workers = len(pong) if pong else 0
    except Exception:  # noqa: BLE001
        workers = None

    overall = "ok" if db_ok == "ok" and redis_ok == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        database=db_ok,
        redis=redis_ok,
        queued_jobs=queued,
        workers_online=workers,
    )
