"""
Celery Application Configuration
Handles async task queue for model retraining, report generation, etc.
"""
from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "agri_price_system",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks.training_tasks", "tasks.data_tasks", "tasks.report_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    beat_schedule={
        "collect-prices-every-6h": {
            "task": "tasks.data_tasks.collect_all_prices",
            "schedule": 6 * 3600,
        },
        "update-predictions-every-4h": {
            "task": "tasks.training_tasks.update_all_predictions",
            "schedule": 4 * 3600,
        },
        "online-learning-daily": {
            "task": "tasks.training_tasks.online_learning_update",
            "schedule": 86400,
        },
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
