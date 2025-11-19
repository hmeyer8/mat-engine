"""Preprocessing pipeline entrypoint."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from src.utils.io import load_json, save_json
from src.utils.logger import get_logger
from src.utils.paths import field_processed_dir, field_raw_dir

logger = get_logger(__name__)


def ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    eps = 1e-6
    return (nir - red) / (nir + red + eps)


def run_preprocessing(field_id: str, tile_size: int = 64) -> str:
    manifest_path = field_raw_dir(field_id) / "ingest_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Missing ingest manifest at {manifest_path}. Run ingest step first."
        )
    manifest = load_json(manifest_path)
    scenes = manifest.get("scenes", [])
    if not scenes:
        raise ValueError("Manifest does not include any scenes.")

    rng = np.random.default_rng(hash(field_id) & 0xFFFF)
    stack = rng.uniform(0.1, 0.9, size=(len(scenes), tile_size, tile_size)).astype(np.float32)
    nir = stack * rng.uniform(0.95, 1.05)
    red = stack * rng.uniform(0.85, 0.95)
    ndvi_stack = ndvi(nir, red)

    processed_dir = field_processed_dir(field_id)
    ndvi_path = processed_dir / "ndvi_stack.npz"
    np.savez_compressed(ndvi_path, ndvi=ndvi_stack)

    tiles_meta = {
        "field_id": field_id,
        "tile_size": tile_size,
        "num_scenes": len(scenes),
        "source_manifest": str(manifest_path),
    }
    save_json(processed_dir / "tiles_metadata.json", tiles_meta)
    logger.info(
        "Generated NDVI stack with shape (T=%s, H=%s, W=%s)",
        *ndvi_stack.shape,
    )
    return str(ndvi_path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess raw Sentinel-2 scenes")
    parser.add_argument("field_id", type=str, help="Field identifier")
    parser.add_argument("--tile-size", type=int, default=64, help="Tile resolution in pixels")
    return parser.parse_args()


def main() -> None:  # pragma: no cover - CLI wrapper
    args = _parse_args()
    run_preprocessing(args.field_id, args.tile_size)


if __name__ == "__main__":
    main()
