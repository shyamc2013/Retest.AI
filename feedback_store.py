"""Persistent, append-only storage for completed attempts."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from config import FEEDBACK_DIR
from models import FeedbackReport


def save_feedback(report: FeedbackReport) -> Path:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"attempt_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    path = FEEDBACK_DIR / f"{stem}.yaml"
    # Preserve every attempt even if two submissions land in the same second.
    suffix = 1
    while path.exists():
        path = FEEDBACK_DIR / f"{stem}_{suffix}.yaml"
        suffix += 1
    path.write_text(yaml.safe_dump(report.model_dump(mode="json"), sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def load_latest_feedback() -> FeedbackReport | None:
    if not FEEDBACK_DIR.exists():
        return None
    attempts = sorted(FEEDBACK_DIR.glob("attempt_*.yaml"))
    if not attempts:
        return None
    try:
        payload = yaml.safe_load(attempts[-1].read_text(encoding="utf-8"))
        return FeedbackReport.model_validate(payload)
    except (OSError, yaml.YAMLError, ValueError):
        return None


def feedback_context() -> str:
    latest = load_latest_feedback()
    if latest is None:
        return "No previous attempt exists. Cover the supplied material broadly."
    return (
        f"Most recent score: {latest.score}\n"
        f"Topic results: {latest.topics}\n"
        f"Weak-area summary: {latest.weak_topics_summary}"
    )


def weak_topics() -> list[str]:
    """Topic names flagged 'weak' in the most recent attempt, if any."""
    latest = load_latest_feedback()
    if latest is None:
        return []
    return [topic for topic, stat in latest.topics.items() if stat.status == "weak"]
