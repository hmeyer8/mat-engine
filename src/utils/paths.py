"""Path utilities for file management."""
from __future__ import annotations

from pathlib import Path

from src.config import get_settings


settings = get_settings()


def field_raw_dir(field_id: str) -> Path:
    path = settings.data.raw / field_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def field_processed_dir(field_id: str) -> Path:
    path = settings.data.processed / field_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def jobs_dir() -> Path:
    settings.data.jobs.mkdir(parents=True, exist_ok=True)
    return settings.data.jobs


def job_path(job_id: str) -> Path:
    return jobs_dir() / f"{job_id}.json"
