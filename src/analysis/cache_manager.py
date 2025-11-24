"""Lightweight tile cache loader used by the public API."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from src.config import PROJECT_ROOT, get_settings
from src.utils.io import load_json
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class TileRecord:
    tile_id: str
    lat: float
    lon: float
    path: Path

    @classmethod
    def from_index(cls, raw: dict, tiles_dir: Path) -> "TileRecord":
        path = raw.get("path") or f"{raw['tile_id']}.json"
        return cls(
            tile_id=raw["tile_id"],
            lat=float(raw["lat"]),
            lon=float(raw["lon"]),
            path=tiles_dir / path,
        )


def point_in_polygon(lon: float, lat: float, polygon: Sequence[Sequence[float]]) -> bool:
    """Ray-casting point-in-polygon; polygon is (lon, lat) pairs."""
    inside = False
    if len(polygon) < 3:
        return inside
    x, y = lon, lat
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        intersects = ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1)
        if intersects:
            inside = not inside
    return inside


class TileCache:
    """Reads cached Nebraska tile JSON files for fast responses."""

    def __init__(self) -> None:
        settings = get_settings()
        self.tiles_dir = settings.cache.tiles_dir
        self.index_path = self.tiles_dir / "index.json"
        self._index = self._load_index()

    def _load_index(self) -> List[TileRecord]:
        index_path = self.index_path
        if not index_path.exists():
            bundled = PROJECT_ROOT / "cache" / "tiles" / "index.json"
            if bundled.exists() and bundled != index_path:
                logger.info("Falling back to bundled tile cache at %s", bundled)
                self.index_path = bundled
                self.tiles_dir = bundled.parent
                index_path = bundled
        if not index_path.exists():
            logger.warning("Tile index missing at %s", index_path)
            return []
        payload = load_json(index_path)
        entries: Iterable[dict] = payload.get("tiles", [])
        records = [TileRecord.from_index(item, self.tiles_dir) for item in entries]
        logger.info("Loaded %d cached tiles from %s", len(records), self.index_path)
        return records

    def _load_tile(self, record: TileRecord) -> dict:
        if not record.path.exists():
            logger.warning("Tile file %s missing for %s", record.path, record.tile_id)
            return {"tile_id": record.tile_id, "missing": True}
        data = load_json(record.path)
        data.setdefault("tile_id", record.tile_id)
        data.setdefault("lat", record.lat)
        data.setdefault("lon", record.lon)
        return data

    def list_tiles(self, bbox: Sequence[float] | None = None) -> List[dict]:
        records = self._index
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            records = [
                record
                for record in records
                if min_lat <= record.lat <= max_lat and min_lon <= record.lon <= max_lon
            ]
        return [self._load_tile(record) for record in records]

    def tiles_for_polygon(self, polygon: Sequence[Sequence[float]]) -> List[dict]:
        """Return tiles whose centroids fall inside the provided polygon."""
        if not polygon:
            return []
        # Ensure polygon is closed for the ray-casting helper
        closed_polygon = list(polygon)
        if polygon[0] != polygon[-1]:
            closed_polygon.append(polygon[0])
        return [
            tile
            for tile in self.list_tiles()
            if point_in_polygon(tile["lon"], tile["lat"], closed_polygon)
        ]
