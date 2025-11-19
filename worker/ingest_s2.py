from __future__ import annotations
import os, json
from pathlib import Path
from datetime import datetime
import numpy as np
import psycopg2
from shapely.geometry import shape, mapping, box
from pystac_client import Client
import planetary_computer as pc
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_geom

def load_geom(aoi_path: Path):
    with open(aoi_path, "r") as f: gj = json.load(f)
    if gj.get("type") == "FeatureCollection": return gj["features"][0]["geometry"]
    if gj.get("type") == "Feature": return gj["geometry"]
    return gj

def search_items(geom_4326, start, end, max_cloud, limit=3):
    client = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    search = client.search(
        collections=["sentinel-2-l2a"],
        intersects=geom_4326,
        datetime=f"{start}/{end}",
        query={"eo:cloud_cover": {"lt": max_cloud}},
        limit=limit,
    )
    return [pc.sign(it) for it in search.get_items()]

def clip_to_aoi(href, geom_4326):
    with rasterio.open(href) as src:
        geom_src = transform_geom("EPSG:4326", src.crs.to_string(), geom_4326)
        data, out_transform = mask(src, [geom_src], crop=True, nodata=src.nodata)
        profile = src.profile.copy()
        profile.update(height=data.shape[1], width=data.shape[2], transform=out_transform)
        return data, profile

def save_tif(path: Path, data: np.ndarray, profile):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst: dst.write(data)

def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    nir = nir.astype("float32"); red = red.astype("float32")
    denom = (nir + red); denom = np.where(denom == 0.0, np.nan, denom)
    return (nir - red) / denom

def to_bbox_polygon(geom_4326):
    g = shape(geom_4326).bounds
    return mapping(box(*g))

def upsert_scene(conn, item_id, sensed_at, tile, cloud, bbox, paths):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO s2_scenes (item_id, sensed_at, mgrs_tile, cloud_cover, bbox, red_path, nir_path, ndvi_path)
            VALUES (%s,%s,%s,%s, ST_GeomFromGeoJSON(%s), %s,%s,%s)
            ON CONFLICT (item_id) DO UPDATE SET
              cloud_cover=EXCLUDED.cloud_cover,
              red_path=EXCLUDED.red_path,
              nir_path=EXCLUDED.nir_path,
              ndvi_path=EXCLUDED.ndvi_path;
        """, (item_id, sensed_at, tile, cloud, json.dumps(bbox), paths["red"], paths["nir"], paths["ndvi"]))
        conn.commit()

def main():
    aoi = Path(os.environ.get("AOI_PATH", "/workspace/aoi/lincoln_ne_aoi.geojson"))
    start = os.environ.get("START_DATE", "2023-06-01")
    end = os.environ.get("END_DATE", "2023-08-31")
    max_cloud = int(os.environ.get("MAX_CLOUD", "20"))
    data_root = Path("/workspace")
    raw_dir = data_root / "data" / "raw" / "sentinel-2"
    proc_dir = data_root / "data" / "processed" / "sentinel-2"

    db_conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "matengine"),
        user=os.environ.get("DB_USER", "matengine"),
        password=os.environ.get("DB_PASS", "matengine"),
    )

    geom = load_geom(aoi)
    items = search_items(geom, start, end, max_cloud, limit=3)
    if not items:
        print("No items found."); return

    for it in items:
        item_id = it.id
        dt = it.properties.get("datetime")
        sensed_at = datetime.fromisoformat(dt.replace("Z","+00:00")) if dt else datetime.utcnow()
        tile = it.properties.get("s2:mgrs_tile", "unknown")
        cloud = float(it.properties.get("eo:cloud_cover", 999))
        bbox = to_bbox_polygon(geom)

        paths = {"red":"", "nir":"", "ndvi":""}
        bands = {"B04":"red", "B08":"nir"}
        clipped = {}

        for band, key in bands.items():
            if band not in it.assets: continue
            href = it.assets[band].href
            arr, profile = clip_to_aoi(href, geom)
            out_dir = raw_dir / f"{sensed_at.date()}_{tile}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{sensed_at.date()}_{tile}_{band}.tif"
            save_tif(out_path, arr, profile)
            clipped[key] = (arr, profile)
            paths[key] = str(out_path)

        if "red" in clipped and "nir" in clipped:
            red_arr, red_prof = clipped["red"]
            nir_arr, _ = clipped["nir"]
            ndvi = compute_ndvi(nir_arr[0], red_arr[0])[None, ...]
            prof = red_prof.copy(); prof.update(count=1, dtype="float32", nodata=np.nan, compress="lzw")
            out_ndvi = proc_dir / f"ndvi_{sensed_at.date()}_{tile}.tif"
            save_tif(out_ndvi, ndvi, prof)
            paths["ndvi"] = str(out_ndvi)

        upsert_scene(db_conn, item_id, sensed_at, tile, cloud, bbox, paths)
        print(f"Ingested {item_id} → {paths}")

    db_conn.close()
    print("Done.")

if __name__ == "__main__":
    main()