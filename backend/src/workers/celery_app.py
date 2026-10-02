"""
Celery app — RITUAL background worker.

Broker: Valkey (BSD-3, replaces Redis — STACK §9 trap #4).
Uses the redis:// URL scheme (Valkey is protocol-compatible).

Beat schedule covers all nightly/weekly tasks from Habit Engine §4–§5
and Failure Layer §3.
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from src.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "ritual",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_broker_url,
    include=[
        "src.workers.tasks.occurrence_generation",
        "src.workers.tasks.miss_detection",
        "src.workers.tasks.fade_evaluation",
        "src.workers.tasks.probe_assignment",
        "src.workers.tasks.stability_scoring",
        "src.workers.tasks.conflict_detection",
        "src.workers.tasks.fresh_start",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=_settings.celery_timezone,
    enable_utc=True,
    task_track_started=True,
    # Prevent tasks from running silently for too long
    task_soft_time_limit=300,
    task_time_limit=600,
)

celery_app.conf.beat_schedule = {
    # Materialize occurrences 7 days ahead (Habit Engine §4.1)
    "occurrence-generation-nightly": {
        "task": "src.workers.tasks.occurrence_generation.generate_occurrences",
        "schedule": crontab(hour=2, minute=0),  # 02:00 UTC nightly
    },
    # Detect missed windows (runs every 30 min; skips 22:00–07:00 per-user local time)
    "miss-detection-frequent": {
        "task": "src.workers.tasks.miss_detection.detect_misses",
        "schedule": crontab(minute="*/30"),
    },
    # Evaluate reminder fading advancement (L0→L4) — Habit Engine §5.2
    "fade-evaluation-daily": {
        "task": "src.workers.tasks.fade_evaluation.evaluate_fading",
        "schedule": crontab(hour=3, minute=0),
    },
    # Assign probe days for the coming week — Habit Engine §5.3
    "probe-assignment-weekly": {
        "task": "src.workers.tasks.probe_assignment.assign_probe_days",
        "schedule": crontab(day_of_week="sunday", hour=1, minute=0),
    },
    # Recompute anchor stability scores — Habit Engine §3
    "stability-scoring-nightly": {
        "task": "src.workers.tasks.stability_scoring.score_anchor_stability",
        "schedule": crontab(hour=1, minute=30),
    },
    # Detect scheduling conflicts over 7-day horizon — Habit Engine §8
    "conflict-detection-nightly": {
        "task": "src.workers.tasks.conflict_detection.detect_conflicts",
        "schedule": crontab(hour=4, minute=0),
    },
    # Fresh-start re-engagement (temporal landmarks) — PRD §4.1.5
    "fresh-start-weekly": {
        "task": "src.workers.tasks.fresh_start.check_fresh_starts",
        "schedule": crontab(day_of_week="friday", hour=12, minute=0),
    },
}
