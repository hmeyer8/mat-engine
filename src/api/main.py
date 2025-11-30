"""FastAPI application exposing MAT Engine insights."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, List
from uuid import uuid4

import numpy as np
import requests
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.analysis.cache_manager import TileCache
from src.config import get_settings
from src.pipeline import run_analysis, run_pipeline
from src.utils.io import load_json, save_json
from src.utils.logger import get_logger
from src.utils.paths import field_processed_dir, field_raw_dir, job_path, jobs_dir

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


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class AnalysisJobRequest(BaseModel):
    field_id: str
    start_date: date
    end_date: date
    zip_code: str | None = None
    polygon: FieldGeometry
    source: str | None = None
    properties: dict[str, Any] | None = None


class JobRecord(BaseModel):
    job_id: str
    field_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    start_date: str
    end_date: str
    zip_code: str
    message: str | None = None
    result: dict[str, Any] | None = None


def _processed_summary_path(field_id: str) -> Path:
    return field_processed_dir(field_id) / "analysis_summary.json"


def _svd_stats_path(field_id: str) -> Path:
    return field_processed_dir(field_id) / "svd_stats.json"


def _ndvi_stack_path(field_id: str) -> Path:
    return field_processed_dir(field_id) / "ndvi_stack.npz"

def _overlay_data_path(field_id: str) -> Path:
    return field_processed_dir(field_id) / "overlay_data.json"


def _utcnow() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _normalize_polygon(geometry: FieldGeometry) -> list:
    coords = geometry.coordinates or []
    if coords and isinstance(coords[0], (list, tuple)) and coords[0] and isinstance(coords[0][0], (list, tuple)):
        polygon = coords[0]
    else:
        polygon = coords
    return polygon


def _persist_field_metadata(
    field_id: str,
    zip_code: str,
    geometry: FieldGeometry,
    source: str | None,
    properties: dict[str, Any] | None,
) -> None:
    payload = {
        "field_id": field_id,
        "zip_code": zip_code,
        "source": source or "ui",
        "geometry": geometry.model_dump(),
        "properties": properties or {},
    }
    save_json(field_raw_dir(field_id) / "field.json", payload)


def _save_job_record(payload: dict) -> dict:
    jobs_dir()
    save_json(job_path(payload["job_id"]), payload)
    return payload


def _load_job_record(job_id: str) -> dict:
    path = job_path(job_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return load_json(path)


def _update_job_record(job_id: str, **updates) -> dict:
    record = _load_job_record(job_id)
    record.update(updates)
    record["updated_at"] = updates.get("updated_at") or _utcnow()
    return _save_job_record(record)


def _fallback_dates(window_days: int = 35, samples: int = 6) -> list[str]:
    today = datetime.utcnow().date()
    step = max(1, window_days // samples)
    return [
        (today - timedelta(days=idx * step)).isoformat()
        for idx in range(samples)
    ]


def _available_dates_for_field(field_id: str) -> tuple[list[str], str]:
    manifest_path = field_raw_dir(field_id) / "ingest_manifest.json"
    if manifest_path.exists():
        try:
            manifest = load_json(manifest_path)
        except Exception:
            logger.warning("Unable to parse manifest for field %s", field_id)
        else:
            scenes = manifest.get("scenes", [])
            manifest_end = manifest.get("end")
            date_values: list[str] = []
            for scene in scenes:
                if not isinstance(scene, dict):
                    continue
                capture = scene.get("capture_ts") or scene.get("date") or manifest_end
                if isinstance(capture, str) and len(capture) >= 10:
                    date_values.append(capture[:10])
            if date_values:
                unique_dates = sorted({val for val in date_values}, reverse=True)
                return unique_dates, "manifest"
    return _fallback_dates(), "synthetic"


def _execute_analysis_job(
    job_id: str,
    field_id: str,
    zip_code: str,
    start_date: str,
    end_date: str,
) -> None:
    try:
        _update_job_record(job_id, status=JobStatus.running.value)
        summary = run_pipeline(
            field_id,
            zip_code=zip_code,
            start=start_date,
            end=end_date,
        )
        result = {
            "summary_path": str(_processed_summary_path(field_id)),
            "analysis": summary,
        }
        _update_job_record(job_id, status=JobStatus.succeeded.value, result=result, message=None)
    except Exception as exc:  # pragma: no cover - background task logging
        logger.exception("Job %s failed", job_id)
        _update_job_record(job_id, status=JobStatus.failed.value, message=str(exc))


def _temporal_trend(field_id: str) -> tuple[str, float]:
    modes_path = field_processed_dir(field_id) / "temporal_modes.json"
    if not modes_path.exists():
        return "stable", 0.0
    payload = load_json(modes_path)
    signature = payload.get("temporal_signature", [])
    if not isinstance(signature, list) or len(signature) < 2:
        return "stable", 0.0
    recent = float(signature[-1])
    baseline = float(signature[max(0, len(signature) - 3)])
    delta = recent - baseline
    threshold = 0.02
    if delta < -threshold:
        return "declining", delta
    if delta > threshold:
        return "recovering", delta
    return "stable", delta


def _manifest_end_date(field_id: str) -> str:
    manifest_path = field_raw_dir(field_id) / "ingest_manifest.json"
    if manifest_path.exists():
        try:
            manifest = load_json(manifest_path)
            end_date = manifest.get("end")
            scenes = manifest.get("scenes", [])
            if not end_date and scenes:
                last_scene = scenes[-1]
                if isinstance(last_scene, dict):
                    end_date = last_scene.get("capture_ts") or last_scene.get("date")
            if isinstance(end_date, str) and len(end_date) >= 10:
                return end_date[:10]
        except Exception:
            logger.warning("Unable to read manifest end date for %s", field_id)
    return datetime.utcnow().date().isoformat()


def _analysis_payload(field_id: str) -> dict:
    summary_path = _processed_summary_path(field_id)
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="Analysis summary not found")
    summary = load_json(summary_path)
    severity = summary.get("stress_label", "unknown")
    health_score = float(summary.get("field_health_score", 0.0))
    trend_label, delta = _temporal_trend(field_id)
    confidence = max(0.5, min(0.95, 1.0 - abs(delta)))
    if severity == "high":
        recommendation = "Prioritise irrigation checks and scout for disease in stressed zones."
    elif severity == "moderate":
        recommendation = "Schedule a field walk to validate stress hotspots before the next irrigation."
    else:
        recommendation = "Continue routine monitoring; no immediate interventions required."
    summary_text = (
        f"CNN+SVD fusion indicates a health score of {health_score:.2f} with {severity} stress "
        f"and a {trend_label} NDVI trend."
    )
    overlays = {
        "cnn": f"/fields/{field_id}/overlay",
        "svd": f"/fields/{field_id}/svd/overlay",
    }
    metrics = {
        "health_score": round(health_score, 4),
    }
    if "cnn" in summary:
        cnn_payload = summary["cnn"]
        metrics["cnn_mean_stress"] = round(float(cnn_payload.get("mean_stress", 0.0)), 4)
    return {
        "field_id": field_id,
        "date": _manifest_end_date(field_id),
        "severity": severity,
        "confidence": round(confidence, 3),
        "trend": trend_label,
        "summary": summary_text,
        "recommendation": recommendation,
        "overlays": overlays,
        "metrics": metrics,
    }


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_OVERPASS_TIMEOUT = 30
MAX_OVERPASS_FEATURES = 400


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


@app.get("/api/available_dates")
def available_dates(field_id: str = Query(..., description="Field identifier")) -> dict:
    dates, source = _available_dates_for_field(field_id)
    return {"field_id": field_id, "dates": dates, "source": source}


@app.post("/api/jobs", status_code=202)
def enqueue_analysis_job(request: AnalysisJobRequest, background_tasks: BackgroundTasks) -> dict:
    if request.end_date < request.start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
    polygon = _normalize_polygon(request.polygon)
    if len(polygon) < 3:
        raise HTTPException(status_code=400, detail="Polygon must contain at least three vertices")
    zip_code = request.zip_code or "00000"
    _persist_field_metadata(
        request.field_id,
        zip_code,
        request.polygon,
        request.source,
        request.properties,
    )
    job_id = uuid4().hex
    timestamp = _utcnow()
    record = JobRecord(
        job_id=job_id,
        field_id=request.field_id,
        status=JobStatus.queued,
        created_at=timestamp,
        updated_at=timestamp,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
        zip_code=zip_code,
        message=None,
        result=None,
    ).model_dump()
    _save_job_record(record)
    background_tasks.add_task(
        _execute_analysis_job,
        job_id,
        request.field_id,
        zip_code,
        request.start_date.isoformat(),
        request.end_date.isoformat(),
    )
    return record


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    return _load_job_record(job_id)


@app.get("/api/analysis/{field_id}")
def analysis_snapshot(field_id: str) -> dict:
    return _analysis_payload(field_id)


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


@app.get("/fields/{field_id}/svd/overlay")
def field_svd_overlay(field_id: str):
    summary = field_summary(field_id)
    svd_path_str = summary.get("svd_overlay_path")
    if not svd_path_str:
        raise HTTPException(status_code=404, detail="SVD overlay not available")
    overlay_path = Path(svd_path_str)
    if not overlay_path.exists():
        raise HTTPException(status_code=404, detail="SVD overlay not found")
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


def _parse_bbox(bbox: str) -> list[float]:
    try:
        coords = [float(val.strip()) for val in bbox.split(",")]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bbox must be comma-separated floats") from exc
    if len(coords) != 4:
        raise HTTPException(status_code=400, detail="bbox must contain four numbers (south,west,north,east)")
    south, west, north, east = coords
    if south >= north or west >= east:
        raise HTTPException(status_code=400, detail="bbox coordinates are invalid")
    return coords


def _build_overpass_query(south: float, west: float, north: float, east: float, crop: str | None = None) -> str:
        crop_clause = "" if not crop else f"  way[\"crop\"=\"{crop}\"]({south},{west},{north},{east});\n  relation[\"crop\"=\"{crop}\"]({south},{west},{north},{east});\n"
        return f"""
[out:json][timeout:{DEFAULT_OVERPASS_TIMEOUT}];
(
  way["landuse"="farmland"]({south},{west},{north},{east});
    way["crop"]({south},{west},{north},{east});
  relation["landuse"="farmland"]({south},{west},{north},{east});
{crop_clause}
);
out geom;
"""


def _fetch_overpass_payload(query: str) -> dict:
    try:
        response = requests.post(OVERPASS_URL, data={"data": query}, timeout=DEFAULT_OVERPASS_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("Overpass request failed")
        raise HTTPException(status_code=502, detail="Overpass API request failed") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Invalid JSON returned by Overpass API") from exc


def _overpass_elements_to_geojson(elements: list[dict], max_features: int) -> dict:
    features: list[dict] = []
    for element in elements:
        geometry = element.get("geometry")
        if not geometry:
            continue
        coords = [[point["lon"], point["lat"]] for point in geometry if "lon" in point and "lat" in point]
        if len(coords) < 3:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        tags = element.get("tags", {})
        feature = {
            "type": "Feature",
            "properties": {
                "field_id": f"osm-{element.get('type')}-{element.get('id')}",
                "name": tags.get("name"),
                "crop": tags.get("crop") or tags.get("landuse"),
                "source": "openstreetmap",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords],
            },
        }
        features.append(feature)
        if len(features) >= max_features:
            break
    return {"type": "FeatureCollection", "features": features}


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


@app.get("/api/fields/osm")
def osm_fields(
    bbox: str = Query(..., description="south,west,north,east"),
    crop: str | None = Query(None, description="Optional crop tag filter"),
    max_features: int = Query(MAX_OVERPASS_FEATURES, ge=1, le=1000),
) -> dict:
    south, west, north, east = _parse_bbox(bbox)
    query = _build_overpass_query(south, west, north, east, crop)
    payload = _fetch_overpass_payload(query)
    geojson = _overpass_elements_to_geojson(payload.get("elements", []), max_features)
    if not geojson["features"]:
        raise HTTPException(status_code=404, detail="No farmland polygons found for bbox")
    return geojson


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
