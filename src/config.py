"""Centralised configuration primitives for MAT Engine."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE, override=False)


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class DataPaths:
    root: Path = PROJECT_ROOT / "data"
    raw: Path = root / "raw"
    processed: Path = root / "processed"


@dataclass(slots=True)
class GPUSettings:
    enabled: bool = _bool(os.getenv("MAT_GPU_ENABLED"), default=False)
    device: str = os.getenv("MAT_GPU_DEVICE", "cuda:0")
    precision: str = os.getenv("MAT_GPU_PRECISION", "fp32")


@dataclass(slots=True)
class ApiSettings:
    host: str = os.getenv("MAT_API_HOST", "0.0.0.0")
    port: int = int(os.getenv("MAT_API_PORT", "8080"))
    cors_origins: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:  # noqa: D401
        origins = os.getenv("MAT_API_CORS", "*")
        self.cors_origins = [o.strip() for o in origins.split(",") if o.strip()]


@dataclass(slots=True)
class SentinelSettings:
    data_dir: Path = (PROJECT_ROOT / os.getenv("MAT_DATA_DIR", "data"))
    api_key: str | None = os.getenv("MAT_SAT_API_KEY")
    tiles_cache_days: int = int(os.getenv("MAT_TILES_CACHE_DAYS", "14"))


@dataclass(slots=True)
class MapsSettings:
    api_key: str | None = os.getenv("MAPS_API_KEY")


@dataclass(slots=True)
class Settings:
    data: DataPaths = field(default_factory=DataPaths)
    gpu: GPUSettings = field(default_factory=GPUSettings)
    api: ApiSettings = field(default_factory=ApiSettings)
    sentinel: SentinelSettings = field(default_factory=SentinelSettings)
    maps: MapsSettings = field(default_factory=MapsSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    settings = Settings()
    settings.data.raw.mkdir(parents=True, exist_ok=True)
    settings.data.processed.mkdir(parents=True, exist_ok=True)
    return settings
