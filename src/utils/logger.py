"""Logging helpers."""
from __future__ import annotations

import logging
from logging import Logger

_LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s - %(message)s"


def get_logger(name: str) -> Logger:
    logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)
    return logging.getLogger(name)
