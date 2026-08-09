"""Celery application instance shared by the worker.

Redis is the broker (and a lightweight result backend for task bookkeeping).
Analysis results themselves always live in Postgres.
"""
from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "repolens",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=60 * 30,  # hard cap: 30 min per analysis job
    worker_prefetch_multiplier=1,
)
