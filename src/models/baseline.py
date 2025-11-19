"""Baseline heuristic stress model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np


@dataclass(slots=True)
class BaselineThresholds:
    low: float = 0.33
    high: float = 0.66


class BaselineStressModel:
    """Simple NDVI-derived stress score useful for demos/tests."""

    def __init__(self, thresholds: BaselineThresholds | None = None) -> None:
        self.thresholds = thresholds or BaselineThresholds()

    def predict(self, ndvi: np.ndarray) -> Dict[str, float | str]:
        if ndvi.ndim != 2:
            raise ValueError("NDVI array must be 2D (H x W).")
        clipped = np.clip(ndvi, 0.0, 1.0)
        mean = float(clipped.mean())
        stress = float(1.0 - mean)
        if stress < self.thresholds.low:
            band = "low"
        elif stress < self.thresholds.high:
            band = "moderate"
        else:
            band = "high"
        return {
            "ndvi_mean": mean,
            "stress_score": stress,
            "label": band,
        }
