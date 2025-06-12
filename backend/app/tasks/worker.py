import os
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# For Celery, we need to setup Redis settings in the new config
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379")

celery_app = Celery(
    "karma_app",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.tasks.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
)

# Configure Celery Beat for scheduled tasks
celery_app.conf.beat_schedule = {
    "check-for-new-posts-every-15-minutes": {
        "task": "tasks.check_for_new_posts_and_generate_drafts",
        "schedule": crontab(minute="*/15"),  # Run every 15 minutes
    },
} 