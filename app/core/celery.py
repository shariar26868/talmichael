"""Celery configuration for background task queue."""

from celery import Celery
from app.core.config import settings

broker = settings.redis_url or "redis://localhost:6379/0"
backend = settings.redis_url or "redis://localhost:6379/0"

celery_app = Celery(
    'nuze',
    broker=broker,
    backend=backend,
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
