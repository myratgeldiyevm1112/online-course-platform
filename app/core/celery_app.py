import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
REDIS_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
    task_ignore_result=True,
    beat_schedule={
        "update-trending-hourly": {
            "task": "app.tasks.tasks.update_trending_courses",
            "schedule": crontab(minute=0),  # каждый час
        },
        "aggregate-analytics-hourly": {
            "task": "app.tasks.tasks.aggregate_analytics",
            "schedule": crontab(minute=30),  # каждый час в :30
        },
        "cleanup-expired-uploads-daily": {
            "task": "app.tasks.tasks.cleanup_expired_uploads",
            "schedule": crontab(hour=3, minute=0),  # каждую ночь в 3:00
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])