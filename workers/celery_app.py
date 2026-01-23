from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
import os

from src.core.config import settings

# Initialize Celery
celery_app = Celery("job_intel")

# Configure Celery
celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_queues={
        "critical": {"exchange": "critical", "routing_key": "critical"},
        "high": {"exchange": "high", "routing_key": "high"},
        "default": {"exchange": "default", "routing_key": "default"},
        "low": {"exchange": "low", "routing_key": "low"},
    },
    # Route tasks to queues based on name
    task_routes={
        "src.tasks.monitoring.*": {"queue": "critical"},
        "src.tasks.scraping.*": {"queue": "default"},
        "src.tasks.cleanup.run_cleanup": {"queue": "low"},
        "src.tasks.cleanup.emergency_disk_cleanup": {"queue": "critical"},
    },
    beat_schedule={
        "scrape-tavily-every-6-hours": {
            "task": "src.tasks.scraping.scrape_source",
            "schedule": crontab(hour="*/6", minute=0),
            "args": ["tavily"],
        },
        "cleanup-expired-daily": {
            "task": "src.tasks.cleanup.run_cleanup",
            "schedule": crontab(hour=3, minute=0),
        },
        "check-resources-every-5-min": {
            "task": "src.tasks.monitoring.check_resources",
            "schedule": 300.0,  # 5 minutes
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(
    ["src.tasks.scraping", "src.tasks.cleanup", "src.tasks.monitoring"]
)
