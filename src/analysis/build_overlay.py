"""Aggregate tile metrics into field overlays."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image

from src.models.baseline import BaselineStressModel
from src.utils.io import load_json, save_json
from src.utils.logger import get_logger
from src.utils.paths import field_processed_dir

logger = get_logger(__name__)


COLOR_SCALE: Tuple[Tuple[int, int, int], ...] = (
    (0, 115, 62),   # green
    (255, 213, 0),  # yellow
    (255, 140, 0),  # orange
    (204, 0, 0),    # red
)


def colorize(stress_map: np.ndarray) -> Image.Image:
    clipped = np.clip(stress_map, 0.0, 1.0)
    steps = len(COLOR_SCALE) - 1
    indices = np.round(clipped * steps).astype(int)
    h, w = clipped.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for idx, color in enumerate(COLOR_SCALE):
        mask = indices == idx
        rgb[mask] = color
    return Image.fromarray(rgb, mode="RGB")


def run_analysis(field_id: str) -> dict:
    processed_dir = field_processed_dir(field_id)
    ndvi_path = processed_dir / "ndvi_stack.npz"
    svd_stats_path = processed_dir / "svd_stats.json"
    if not ndvi_path.exists():
        raise FileNotFoundError("Run preprocessing before analysis.")
    if not svd_stats_path.exists():
        raise FileNotFoundError("Run temporal SVD before analysis.")

    ndvi_stack = np.load(ndvi_path)["ndvi"]
    last_snapshot = ndvi_stack[-1]
    model = BaselineStressModel()
    field_summary = model.predict(ndvi_stack.mean(axis=0))
    stress_map = 1.0 - np.clip(last_snapshot, 0.0, 1.0)
    overlay_img = colorize(stress_map)

    overlay_path = processed_dir / "overlay.png"
    overlay_img.save(overlay_path)

    summary = {
        "field_id": field_id,
        "field_health_score": round(1.0 - field_summary["stress_score"], 4),
        "stress_label": field_summary["label"],
        "overlay_path": str(overlay_path),
        "svd_stats_path": str(svd_stats_path),
    }
    save_json(processed_dir / "analysis_summary.json", summary)
    logger.info(
        "Built field overlay for %s: score %.3f (%s)",
        field_id,
        summary["field_health_score"],
        summary["stress_label"],
    )
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate tile metrics into field overlay")
    parser.add_argument("field_id", type=str, help="Field identifier")
    return parser.parse_args()


def main() -> None:  # pragma: no cover
    args = _parse_args()
    run_analysis(args.field_id)


if __name__ == "__main__":
    main()
