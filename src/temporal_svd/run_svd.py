"""Temporal SVD pipeline for tile stacks."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

import numpy as np

from src.utils.io import load_json, save_json
from src.utils.logger import get_logger
from src.utils.paths import field_processed_dir

logger = get_logger(__name__)


def compute_tile_svd(ndvi_stack: np.ndarray, rank: int) -> Dict[str, float | list[float]]:
    """Compute truncated SVD statistics for an NDVI stack."""
    time_steps, height, width = ndvi_stack.shape
    matrix = ndvi_stack.reshape(time_steps, height * width)
    u, s, vt = np.linalg.svd(matrix, full_matrices=False)
    k = min(rank, len(s))
    explained = (s[:k] ** 2) / (s**2).sum()
    return {
        "rank": int(k),
        "singular_values": s[:k].round(6).tolist(),
        "explained_variance": explained.round(6).tolist(),
    }


def run_svd(field_id: str, rank: int = 3) -> str:
    processed_dir = field_processed_dir(field_id)
    ndvi_path = processed_dir / "ndvi_stack.npz"
    if not ndvi_path.exists():
        raise FileNotFoundError(
            f"Missing NDVI stack at {ndvi_path}. Run preprocessing first."
        )
    ndvi_data = np.load(ndvi_path)
    if "ndvi" not in ndvi_data:
        raise KeyError("ndvi_stack.npz does not contain 'ndvi' array")
    ndvi_stack = ndvi_data["ndvi"]
    stats = compute_tile_svd(ndvi_stack, rank=rank)
    stats_payload = {
        "field_id": field_id,
        "rank": stats["rank"],
        "singular_values": stats["singular_values"],
        "explained_variance": stats["explained_variance"],
        "source": str(ndvi_path),
    }
    save_json(processed_dir / "svd_stats.json", stats_payload)

    temporal_modes = ndvi_stack.mean(axis=(1, 2)).tolist()
    save_json(processed_dir / "temporal_modes.json", {
        "field_id": field_id,
        "temporal_signature": temporal_modes,
    })
    logger.info(
        "Computed SVD for field %s with rank %s (top singular value %.4f)",
        field_id,
        stats_payload["rank"],
        stats_payload["singular_values"][0] if stats_payload["singular_values"] else 0.0,
    )
    return str(processed_dir / "svd_stats.json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute temporal SVD for NDVI stack")
    parser.add_argument("field_id", type=str, help="Field identifier")
    parser.add_argument("--rank", type=int, default=3, help="Truncation rank")
    return parser.parse_args()


def main() -> None:  # pragma: no cover
    args = _parse_args()
    run_svd(args.field_id, rank=args.rank)


if __name__ == "__main__":
    main()
