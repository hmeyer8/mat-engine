"""FastAPI application exposing MAT Engine insights."""
from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.analysis.cache_manager import TileCache
from src.config import get_settings
from src.pipeline import run_analysis
from src.utils.io import load_json, save_json
from src.utils.logger import get_logger
from src.utils.paths import field_processed_dir, field_raw_dir

logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(title="MAT Engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tile_cache = TileCache()


class FieldGeometry(BaseModel):
    type: str = Field(examples=["Polygon"])
    coordinates: List


class FieldRegistration(BaseModel):
    field_id: str
    zip_code: str
    geometry: FieldGeometry


class AnalyzeFieldRequest(BaseModel):
    field_id: str | None = None
    polygon: FieldGeometry


def _processed_summary_path(field_id: str) -> Path:
    return field_processed_dir(field_id) / "analysis_summary.json"


def _svd_stats_path(field_id: str) -> Path:
    return field_processed_dir(field_id) / "svd_stats.json"


def _ndvi_stack_path(field_id: str) -> Path:
    return field_processed_dir(field_id) / "ndvi_stack.npz"

def _overlay_data_path(field_id: str) -> Path:
    return field_processed_dir(field_id) / "overlay_data.json"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/ping")
def ping() -> dict:
    return {"status": "ok", "environment": settings.api.environment, "port": settings.api.port}


@app.post("/fields", status_code=201)
def register_field(payload: FieldRegistration) -> dict:
    meta = payload.model_dump()
    raw_dir = field_raw_dir(payload.field_id)
    meta_path = raw_dir / "field.json"
    save_json(meta_path, meta)
    logger.info("Registered field %s (zip %s)", payload.field_id, payload.zip_code)
    return {"message": "field registered", "field_id": payload.field_id}


@app.get("/fields/{field_id}/summary")
def field_summary(field_id: str) -> dict:
    summary_path = _processed_summary_path(field_id)
    if not summary_path.exists():
        run_analysis(field_id)
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="Summary not found. Run pipeline.")
    return load_json(summary_path)


@app.get("/fields/{field_id}/overlay")
def field_overlay(field_id: str):
    summary = field_summary(field_id)
    overlay_path = Path(summary["overlay_path"])
    if not overlay_path.exists():
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(overlay_path, media_type="image/png")


@app.get("/fields/{field_id}/overlay/data")
def field_overlay_data(field_id: str) -> dict:
    """Return numeric overlay grid + bounds for map rendering."""
    summary = field_summary(field_id)
    data_path = _overlay_data_path(field_id)
    if not data_path.exists():
        # Trigger regeneration if missing
        run_analysis(field_id)
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="Overlay data not found")
    return load_json(data_path)


@app.get("/fields/{field_id}/indices/{index_name}")
def field_index(field_id: str, index_name: str) -> dict:
    if index_name.lower() != "ndvi":
        raise HTTPException(status_code=400, detail="Only NDVI is supported in the prototype")
    ndvi_path = _ndvi_stack_path(field_id)
    if not ndvi_path.exists():
        raise HTTPException(status_code=404, detail="NDVI stack missing")
    ndvi_stack = np.load(ndvi_path)["ndvi"]
    profile = ndvi_stack.mean(axis=(1, 2)).tolist()
    return {
        "field_id": field_id,
        "index": "ndvi",
        "temporal_profile": profile,
        "latest": profile[-1],
    }


@app.get("/fields/{field_id}/svd/stats")
def svd_stats(field_id: str) -> dict:
    path = _svd_stats_path(field_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run temporal SVD first")
    return load_json(path)


@app.get("/tiles")
def list_tiles(bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat")) -> dict:
    parsed_bbox = None
    if bbox:
        try:
            coords = [float(val) for val in bbox.split(",")]
            if len(coords) != 4:
                raise ValueError
            parsed_bbox = coords
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="bbox must be four comma-separated numbers") from exc
    tiles = tile_cache.list_tiles(parsed_bbox)
    return {"count": len(tiles), "tiles": tiles}


@app.post("/analyze-field")
def analyze_field(request: AnalyzeFieldRequest) -> dict:
    geometry = request.polygon
    coords = geometry.coordinates or []
    if geometry.type.lower() != "polygon":
        raise HTTPException(status_code=400, detail="Only Polygon geometry is supported")
    if coords and isinstance(coords[0], (list, tuple)) and coords[0] and isinstance(coords[0][0], (list, tuple)):
        polygon_coords = coords[0]
    else:
        polygon_coords = coords
    if len(polygon_coords) < 3:
        raise HTTPException(status_code=400, detail="Polygon must contain at least three vertices")
    tiles = tile_cache.tiles_for_polygon(polygon_coords)
    return {
        "field_id": request.field_id,
        "tile_count": len(tiles),
        "tiles": tiles,
        "source": "cache",
    }
