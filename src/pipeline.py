"""Unified ingest → preprocess → SVD → overlay pipeline with optional CNN scoring."""
from __future__ import annotations

import argparse
import os
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import requests
from PIL import Image
from rasterio.io import MemoryFile

from src.config import get_settings
from src.models.baseline import BaselineStressModel
from src.utils.io import load_json, save_json
from src.utils.logger import get_logger
from src.utils.paths import field_processed_dir, field_raw_dir

logger = get_logger(__name__)

# Optional torch import for lightweight CNN inference
try:  # pragma: no cover - exercised only when torch is installed
    import torch
    import torch.nn as nn
except Exception:  # pragma: no cover - keep pipeline runnable without torch
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]


COLOR_SCALE: Tuple[Tuple[int, int, int], ...] = (
    (0, 115, 62),   # green
    (255, 213, 0),  # yellow
    (255, 140, 0),  # orange
    (204, 0, 0),    # red
)


def _colorize(stress_map: np.ndarray) -> Image.Image:
    clipped = np.clip(stress_map, 0.0, 1.0)
    steps = len(COLOR_SCALE) - 1
    indices = np.round(clipped * steps).astype(int)
    h, w = clipped.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for idx, color in enumerate(COLOR_SCALE):
        mask = indices == idx
        rgb[mask] = color
    return Image.fromarray(rgb, mode="RGB")


def _ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    eps = 1e-6
    return (nir - red) / (nir + red + eps)


def _conv2d_numpy(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Tiny 2D convolution used when torch is unavailable."""
    pad = kernel.shape[0] // 2
    padded = np.pad(image, pad, mode="edge")
    h, w = image.shape
    out = np.zeros_like(image, dtype=np.float32)
    for i in range(h):
        for j in range(w):
            region = padded[i : i + kernel.shape[0], j : j + kernel.shape[1]]
            out[i, j] = float((region * kernel).sum())
    out = (out - out.min()) / (out.max() - out.min() + 1e-6)
    return out


def _primary_svd_mode(ndvi_stack: np.ndarray) -> np.ndarray:
    """Return the spatial mode associated with the top singular vector."""
    time_steps, height, width = ndvi_stack.shape
    matrix = ndvi_stack.reshape(time_steps, height * width)
    _, _, vt = np.linalg.svd(matrix, full_matrices=False)
    primary = vt[0].reshape(height, width)
    normalized = (primary - primary.min()) / (primary.max() - primary.min() + 1e-6)
    return normalized.astype(np.float32)


if nn is not None:  # pragma: no cover - only defined when torch is present
    class _TinyCNN(nn.Module):  # type: ignore[misc]
        """Very small CNN used for stress scoring."""

        def __init__(self) -> None:
            super().__init__()
            self.layers = nn.Sequential(
                nn.Conv2d(1, 8, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.Conv2d(8, 16, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.Conv2d(16, 1, kernel_size=1),
            )

        def forward(self, x):
            return torch.sigmoid(self.layers(x))
else:
    class _TinyCNN:  # pragma: no cover - placeholder
        """Placeholder to satisfy type checkers when torch is missing."""

        def __init__(self) -> None:
            raise RuntimeError("Torch is not installed; CNN unavailable.")


@dataclass(slots=True)
class CNNStressModel:
    """Wrap CNN inference with a numpy fallback so the pipeline stays dependency-light."""

    device: str = "cpu"
    available: bool = field(init=False, default=False)
    model: _TinyCNN | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.available = torch is not None and nn is not None
        if self.available:
            self.model = _TinyCNN().to(self.device)
            self.model.eval()

    def predict(self, ndvi_stack: np.ndarray) -> Dict[str, object]:
        latest = np.clip(ndvi_stack[-1], 0.0, 1.0)
        if self.available:
            assert self.model is not None  # mypy guard
            tensor = torch.from_numpy(latest.astype(np.float32)).unsqueeze(0).unsqueeze(0)
            tensor = tensor.to(self.device)
            with torch.no_grad():
                stress = self.model(tensor).squeeze().cpu().numpy()
            mode = "tiny-cnn"
        else:
            kernel = np.array([[0.05, 0.1, 0.05], [0.1, 0.4, 0.1], [0.05, 0.1, 0.05]], dtype=np.float32)
            stress = _conv2d_numpy(latest, kernel)
            mode = "numpy-fallback"
        return {"stress_map": np.clip(stress, 0.0, 1.0), "mode": mode}


def run_ingest(field_id: str, zip_code: str, start: str, end: str) -> str:
    """Ingest step: prefer Copernicus NDVI fetch when creds+geometry are available, else mock."""
    # Try real NDVI fetch first
    geometry = _load_geometry(field_id)
    cdse_client_id = os.getenv("CDSE_CLIENT_ID")
    cdse_client_secret = os.getenv("CDSE_CLIENT_SECRET")
    if geometry and cdse_client_id and cdse_client_secret:
        logger.info("Attempting Copernicus NDVI ingest for field %s", field_id)
        ndvi_path = _download_ndvi_from_cdse(
            field_id,
            geometry=geometry,
            start=start,
            end=end,
            client_id=cdse_client_id,
            client_secret=cdse_client_secret,
        )
        logger.info("Fetched NDVI from Copernicus to %s", ndvi_path)
        return str(ndvi_path)

    # Fallback to synthetic ingest
    logger.info("Copernicus creds/geometry missing; using simulated ingest for %s", field_id)
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    scenes = []
    seed = hash((field_id, zip_code, start, end)) & 0xFFFF
    rng = random.Random(seed)
    days = (end_dt - start_dt).days or 1
    for idx in range(min(5, days)):
        capture = start_dt + (end_dt - start_dt) * (idx / max(1, days))
        scenes.append(
            {
                "scene_id": f"S2A_{field_id}_{idx:02d}",
                "capture_ts": capture.isoformat(),
                "cloud_cover": round(rng.uniform(0, 0.4), 3),
                "zip_code": zip_code,
            }
        )
    payload = {
        "field_id": field_id,
        "zip_code": zip_code,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "scenes": scenes,
        "notes": "Simulated ingest metadata. Replace with real Sentinel-2 fetch logic.",
    }
    raw_dir = field_raw_dir(field_id)
    path = raw_dir / "ingest_manifest.json"
    save_json(path, payload)
    logger.info("Wrote ingest manifest to %s", path)
    return str(path)


def _load_geometry(field_id: str) -> dict | None:
    field_meta = field_raw_dir(field_id) / "field.json"
    if not field_meta.exists():
        return None
    payload = load_json(field_meta)
    return payload.get("geometry")


def _geometry_bounds(geometry: dict | None) -> dict | None:
    """Compute min/max lon/lat bounds from GeoJSON-like polygon."""
    if not geometry:
        return None
    coords = geometry.get("coordinates")
    if not coords:
        return None
    # Handle Polygon as list-of-rings or flat
    ring = coords[0] if isinstance(coords[0][0], (list, tuple)) else coords
    lons = [pt[0] for pt in ring]
    lats = [pt[1] for pt in ring]
    return {
        "min_lon": min(lons),
        "min_lat": min(lats),
        "max_lon": max(lons),
        "max_lat": max(lats),
    }


def _fetch_cdse_token(client_id: str, client_secret: str) -> str:
    cached = _read_cached_token()
    if cached:
        return cached
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "openid profile email",
    }
    response = requests.post(token_url, data=data, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"CDSE token request failed: {response.status_code} {response.text}")
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("CDSE token response missing access_token")
    expires_in = response.json().get("expires_in", 0)
    _write_cached_token(token, expires_in)
    return token


def _token_cache_path() -> Path:
    settings = get_settings()
    return settings.cache.root / "cdse_token.json"


def _read_cached_token() -> str | None:
    path = _token_cache_path()
    if not path.exists():
        return None
    try:
        payload = load_json(path)
    except Exception:
        return None
    expires_at = payload.get("expires_at", 0)
    # Include small buffer to avoid using an about-to-expire token
    if time.time() < expires_at - 60:
        return payload.get("access_token")
    return None


def _write_cached_token(token: str, expires_in: int) -> None:
    path = _token_cache_path()
    try:
        payload = {
            "access_token": token,
            "expires_at": time.time() + int(expires_in),
        }
        save_json(path, payload)
    except Exception:
        # Non-fatal; proceed without caching
        logger.warning("Unable to cache Copernicus token at %s", path)


def _download_ndvi_from_cdse(
    field_id: str,
    geometry: dict,
    start: str,
    end: str,
    client_id: str,
    client_secret: str,
) -> Path:
    """Call Copernicus Process API to retrieve NDVI for the field polygon."""
    token = _fetch_cdse_token(client_id, client_secret)
    evalscript = """//VERSION=3
function setup() {
  return {
    input: ["B04", "B08"],
    output: { bands: 1, sampleType: "FLOAT32" }
  };
}
function evaluatePixel(sample) {
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 0.0001);
  return [ndvi];
}
"""
    payload = {
        "input": {
            "bounds": {"geometry": geometry},
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {"from": f"{start}T00:00:00Z", "to": f"{end}T23:59:59Z"},
                        "mosaickingOrder": "mostRecent",
                    },
                }
            ],
        },
        "output": {
            "width": 256,
            "height": 256,
            "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}],
        },
        "evalscript": evalscript,
    }
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://sh.dataspace.copernicus.eu/api/v1/process"
    response = requests.post(url, json=payload, headers=headers, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(f"CDSE process request failed: {response.status_code} {response.text}")

    processed_dir = field_processed_dir(field_id)
    ndvi_path = processed_dir / "ndvi_stack.npz"
    with MemoryFile(response.content) as memfile:
        with memfile.open() as dataset:
            ndvi = dataset.read(1).astype(np.float32)
    np.savez_compressed(ndvi_path, ndvi=np.expand_dims(ndvi, axis=0))

    # Persist minimal manifest to match mock workflow expectations
    raw_dir = field_raw_dir(field_id)
    save_json(
        raw_dir / "ingest_manifest.json",
        {
            "field_id": field_id,
            "zip_code": "",
            "start": start,
            "end": end,
            "scenes": [{"scene_id": "cdse_ndvi_mosaic", "capture_ts": end, "cloud_cover": None}],
            "notes": "NDVI fetched via Copernicus Process API",
        },
    )
    return ndvi_path


def run_preprocessing(field_id: str, tile_size: int = 64) -> str:
    """Generate a synthetic NDVI stack for the provided field."""
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
    ndvi_stack = _ndvi(nir, red)

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
    logger.info("Generated NDVI stack with shape (T=%s, H=%s, W=%s)", *ndvi_stack.shape)
    return str(ndvi_path)


def compute_temporal_svd(ndvi_stack: np.ndarray, rank: int) -> Dict[str, float | list[float]]:
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


def run_temporal_svd(field_id: str, rank: int = 3, ndvi_stack: np.ndarray | None = None) -> Dict[str, object]:
    """Persist temporal SVD stats to disk and return the payload."""
    processed_dir = field_processed_dir(field_id)
    ndvi_path = processed_dir / "ndvi_stack.npz"
    if ndvi_stack is None:
        if not ndvi_path.exists():
            raise FileNotFoundError(f"Missing NDVI stack at {ndvi_path}. Run preprocessing first.")
        ndvi_data = np.load(ndvi_path)
        if "ndvi" not in ndvi_data:
            raise KeyError("ndvi_stack.npz does not contain 'ndvi' array")
        ndvi_stack = ndvi_data["ndvi"]
    stats = compute_temporal_svd(ndvi_stack, rank=rank)
    stats_payload = {
        "field_id": field_id,
        "rank": stats["rank"],
        "singular_values": stats["singular_values"],
        "explained_variance": stats["explained_variance"],
        "source": str(ndvi_path),
    }
    save_json(processed_dir / "svd_stats.json", stats_payload)

    temporal_modes = ndvi_stack.mean(axis=(1, 2)).tolist()
    save_json(
        processed_dir / "temporal_modes.json",
        {"field_id": field_id, "temporal_signature": temporal_modes},
    )
    logger.info(
        "Computed SVD for field %s with rank %s (top singular value %.4f)",
        field_id,
        stats_payload["rank"],
        stats_payload["singular_values"][0] if stats_payload["singular_values"] else 0.0,
    )
    return stats_payload


def run_analysis(field_id: str, *, rank: int = 3, use_cnn: bool = True, cnn_device: str = "cpu") -> dict:
    """Aggregate pipeline outputs into overlay and summary (baseline + optional CNN)."""
    processed_dir = field_processed_dir(field_id)
    ndvi_path = processed_dir / "ndvi_stack.npz"
    if not ndvi_path.exists():
        raise FileNotFoundError("Run preprocessing before analysis.")

    ndvi_stack = np.load(ndvi_path)["ndvi"]
    svd_stats_path = processed_dir / "svd_stats.json"
    if not svd_stats_path.exists():
        svd_stats = run_temporal_svd(field_id, rank=rank, ndvi_stack=ndvi_stack)
    else:
        svd_stats = load_json(svd_stats_path)

    baseline_model = BaselineStressModel()
    baseline_summary = baseline_model.predict(ndvi_stack.mean(axis=0))

    stress_map = 1.0 - np.clip(ndvi_stack[-1], 0.0, 1.0)
    cnn_result: Dict[str, object] | None = None
    if use_cnn:
        cnn_model = CNNStressModel(device=cnn_device)
        cnn_result = cnn_model.predict(ndvi_stack)
        stress_map = 0.6 * stress_map + 0.4 * cnn_result["stress_map"]  # type: ignore[index]

    svd_overlay = _primary_svd_mode(ndvi_stack)

    overlay_img = _colorize(stress_map)
    overlay_path = processed_dir / "overlay.png"
    overlay_img.save(overlay_path)

    svd_overlay_img = _colorize(svd_overlay)
    svd_overlay_path = processed_dir / "svd_overlay.png"
    svd_overlay_img.save(svd_overlay_path)

    summary = {
        "field_id": field_id,
        "field_health_score": round(1.0 - baseline_summary["stress_score"], 4),
        "stress_label": baseline_summary["label"],
        "overlay_path": str(overlay_path),
        "svd_overlay_path": str(svd_overlay_path),
        "svd_stats_path": str(processed_dir / "svd_stats.json"),
    }
    if cnn_result:
        summary["cnn"] = {
            "mode": cnn_result["mode"],
            "mean_stress": float(np.mean(cnn_result["stress_map"])),  # type: ignore[index]
        }
    # Save numeric overlay data for map rendering
    bounds = _geometry_bounds(_load_geometry(field_id))
    overlay_data = {
        "field_id": field_id,
        "shape": list(stress_map.shape),
        "bounds": bounds,
        "values": stress_map.tolist(),
        "colormap": COLOR_SCALE,
    }
    overlay_data_path = processed_dir / "overlay_data.json"
    save_json(overlay_data_path, overlay_data)
    summary["overlay_data_path"] = str(overlay_data_path)

    svd_overlay_payload = {
        "field_id": field_id,
        "shape": list(svd_overlay.shape),
        "bounds": bounds,
        "values": svd_overlay.tolist(),
        "colormap": COLOR_SCALE,
        "mode": "temporal-primary",
    }
    svd_overlay_data_path = processed_dir / "svd_overlay_data.json"
    save_json(svd_overlay_data_path, svd_overlay_payload)
    summary["svd_overlay_data_path"] = str(svd_overlay_data_path)

    save_json(processed_dir / "analysis_summary.json", summary)
    logger.info(
        "Built field overlay for %s: score %.3f (%s)",
        field_id,
        summary["field_health_score"],
        summary["stress_label"],
    )
    return summary


def run_pipeline(
    field_id: str,
    zip_code: str,
    start: str,
    end: str,
    *,
    tile_size: int = 64,
    rank: int = 3,
    use_cnn: bool = True,
    cnn_device: str = "cpu",
) -> dict:
    """End-to-end convenience wrapper for the full pipeline."""
    run_ingest(field_id, zip_code=zip_code, start=start, end=end)
    run_preprocessing(field_id, tile_size=tile_size)
    run_temporal_svd(field_id, rank=rank)
    return run_analysis(field_id, rank=rank, use_cnn=use_cnn, cnn_device=cnn_device)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MAT Engine unified pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="Simulate ingest")
    ingest_p.add_argument("field_id")
    ingest_p.add_argument("zip_code")
    ingest_p.add_argument("start")
    ingest_p.add_argument("end")

    prep_p = sub.add_parser("preprocess", help="Build NDVI stack")
    prep_p.add_argument("field_id")
    prep_p.add_argument("--tile-size", type=int, default=64)

    svd_p = sub.add_parser("svd", help="Compute temporal SVD")
    svd_p.add_argument("field_id")
    svd_p.add_argument("--rank", type=int, default=3)

    overlay_p = sub.add_parser("analyze", help="Generate overlay + summary")
    overlay_p.add_argument("field_id")
    overlay_p.add_argument("--rank", type=int, default=3)
    overlay_p.add_argument("--no-cnn", action="store_true", help="Skip CNN fusion")
    overlay_p.add_argument("--cnn-device", default="cpu")

    pipe_p = sub.add_parser("pipeline", help="Run ingest→overlay")
    pipe_p.add_argument("field_id")
    pipe_p.add_argument("zip_code")
    pipe_p.add_argument("start")
    pipe_p.add_argument("end")
    pipe_p.add_argument("--tile-size", type=int, default=64)
    pipe_p.add_argument("--rank", type=int, default=3)
    pipe_p.add_argument("--no-cnn", action="store_true", help="Skip CNN fusion")
    pipe_p.add_argument("--cnn-device", default="cpu")
    return parser


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "ingest":
        run_ingest(args.field_id, args.zip_code, args.start, args.end)
    elif args.command == "preprocess":
        run_preprocessing(args.field_id, tile_size=args.tile_size)
    elif args.command == "svd":
        run_temporal_svd(args.field_id, rank=args.rank)
    elif args.command == "analyze":
        run_analysis(args.field_id, rank=args.rank, use_cnn=not args.no_cnn, cnn_device=args.cnn_device)
    elif args.command == "pipeline":
        run_pipeline(
            args.field_id,
            args.zip_code,
            args.start,
            args.end,
            tile_size=args.tile_size,
            rank=args.rank,
            use_cnn=not args.no_cnn,
            cnn_device=args.cnn_device,
        )
    else:
        parser.error("Unsupported command")


if __name__ == "__main__":  # pragma: no cover
    main()
