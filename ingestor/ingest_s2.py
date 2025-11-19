from __future__ import annotations
import os, json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import numpy as np
from shapely.geometry import shape, mapping, box
from pystac_client import Client
import planetary_computer as pc
import rasterio
from rasterio.mask import mask
from rasterio.warp import transform_geom
from PIL import Image
from rasterio.warp import transform_bounds


def load_geom(aoi_path: Path) -> Dict[str, Any]:
    with open(aoi_path, "r") as f:
        gj = json.load(f)
    if gj.get("type") == "FeatureCollection":
        return gj["features"][0]["geometry"]
    if gj.get("type") == "Feature":
        return gj["geometry"]
    return gj


def search_items(geom_4326, start: str, end: str, max_cloud: int, limit: int = 2):
    client = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    search = client.search(
        collections=["sentinel-2-l2a"],
        intersects=geom_4326,
        datetime=f"{start}/{end}",
        query={"eo:cloud_cover": {"lt": max_cloud}},
        limit=limit,
    )
    return [pc.sign(it) for it in search.get_items()]


def clip_to_aoi(href: str, geom_4326):
    with rasterio.open(href) as src:
        geom_src = transform_geom("EPSG:4326", src.crs.to_string(), geom_4326)
        data, out_transform = mask(src, [geom_src], crop=True, nodata=src.nodata)
        profile = src.profile.copy()
        profile.update(height=data.shape[1], width=data.shape[2], transform=out_transform)
        return data, profile


def save_tif(path: Path, data: np.ndarray, profile):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    nir = nir.astype("float32"); red = red.astype("float32")
    denom = (nir + red)
    denom = np.where(denom == 0.0, np.nan, denom)
    return (nir - red) / denom


def save_png_preview(ndvi: np.ndarray, out_png: Path):
    # Map NDVI [-1,1] -> [0,255]
    arr = np.clip((ndvi + 1) / 2, 0, 1)
    img = (arr * 255).astype("uint8")
    im = Image.fromarray(img)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_png)


def save_png_color_overlay(ndvi: np.ndarray, out_png: Path):
    # Colormap from red (-1) -> yellow (0) -> green (1), transparent on NaN
    a = ndvi.copy()
    mask = np.isnan(a)
    a = np.clip((a + 1) / 2, 0, 1)  # [0..1]
    # Two-segment gradient: [0..0.5] red->yellow, [0.5..1] yellow->green
    r = np.where(a < 0.5, 1.0, 2.0 - 2.0 * a)  # 1..0
    g = np.where(a < 0.5, 2.0 * a, 1.0)        # 0..1
    b = np.zeros_like(a)
    # Scale to 8-bit
    R = (np.clip(r, 0, 1) * 255).astype("uint8")
    G = (np.clip(g, 0, 1) * 255).astype("uint8")
    B = (np.clip(b, 0, 1) * 255).astype("uint8")
    A = np.where(mask, 0, 200).astype("uint8")  # semi-transparent
    rgba = np.dstack([R, G, B, A])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(out_png)


def save_png_rgb(b04: np.ndarray, b03: np.ndarray, b02: np.ndarray, out_png: Path):
    # Simple normalization for quicklook: divide by 3000 and clip [0,1]
    def norm(b):
        x = b.astype("float32")
        x = x / 3000.0
        x = np.clip(x, 0, 1)
        return (x * 255).astype("uint8")

    R = norm(b04)
    G = norm(b03)
    B = norm(b02)
    rgb = np.dstack([R, G, B])
    out_png.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, mode="RGB").save(out_png)


def save_png_hot_overlay(ndvi: np.ndarray, out_png: Path, thresh: float = 0.6):
        """
        Produce a red heat overlay where:
        - Pixels with NDVI < thresh are transparent.
        - Pixels >= thresh are colored from light red (near threshold) to dark red (strong NDVI).
            This maps intensity to brightness (darker red = stronger signal) rather than just alpha.
        """
        a = ndvi.copy().astype("float32")
        mask_nan = np.isnan(a)

        # Normalize intensity from threshold..1 to 0..1
        val = (a - thresh) / max(1e-6, (1.0 - thresh))
        val = np.clip(val, 0.0, 1.0)

        # Define light and dark red endpoints
        light = np.array([255, 160, 160], dtype="float32")  # pale red
        dark = np.array([128,   0,   0], dtype="float32")  # dark red

        # Lerp per channel: color = (1-val)*light + val*dark  (darker for stronger)
        R = ((1.0 - val) * light[0] + val * dark[0]).astype("uint8")
        G = ((1.0 - val) * light[1] + val * dark[1]).astype("uint8")
        B = ((1.0 - val) * light[2] + val * dark[2]).astype("uint8")

        # Alpha: constant where val>0, transparent otherwise; hide NaNs
        A = np.where(val > 0.0, 200, 0).astype("uint8")
        A = np.where(mask_nan, 0, A)

        rgba = np.dstack([R, G, B, A])
        out_png.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgba, mode="RGBA").save(out_png)


def to_bbox_polygon(geom_4326):
    minx, miny, maxx, maxy = shape(geom_4326).bounds
    return mapping(box(minx, miny, maxx, maxy))


def process_geom(geom, start: str, end: str, max_cloud: int, limit: int, hot_thresh: float):
    aoi_path = Path(os.environ.get("AOI_PATH", "/workspace/data/aoi/lincoln_ne_aoi.geojson"))
    data_root = Path("/workspace/data")
    raw_dir = data_root / "raw" / "sentinel-2"
    proc_dir = data_root / "processed" / "sentinel-2"

    items = search_items(geom, start, end, max_cloud, limit=limit)
    if not items:
        print("No Sentinel-2 items found for given filters.")
        return

    for it in items:
        dt = it.properties.get("datetime")
        sensed_at = datetime.fromisoformat(dt.replace("Z", "+00:00")) if dt else datetime.utcnow()
        date = sensed_at.date().isoformat()
        tile = it.properties.get("s2:mgrs_tile", "unknown")

        clipped = {}
        for band in ("B02", "B03", "B04", "B08"):  # Blue, Green, Red, NIR
            if band not in it.assets:
                continue
            href = it.assets[band].href
            arr, profile = clip_to_aoi(href, geom)
            out_dir = raw_dir / f"{date}_{tile}"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{date}_{tile}_{band}.tif"
            save_tif(out_path, arr, profile)
            clipped[band] = (arr, profile)
            print(f"Saved {out_path}")

        if "B04" in clipped and "B08" in clipped:
            red, red_prof = clipped["B04"]
            nir, _ = clipped["B08"]
            ndvi = compute_ndvi(nir[0], red[0])  # (H,W)
            # Save GeoTIFF
            ndvi_prof = red_prof.copy(); ndvi_prof.update(count=1, dtype="float32", nodata=np.nan, compress="lzw")
            out_tif = proc_dir / f"ndvi_{date}_{tile}.tif"
            save_tif(out_tif, ndvi[None, ...], ndvi_prof)
            # Save PNG preview
            out_png = proc_dir / f"ndvi_{date}_{tile}.png"
            save_png_preview(ndvi, out_png)
            # Save colorized overlay with transparency
            out_color = proc_dir / f"ndvi_{date}_{tile}_color.png"
            save_png_color_overlay(ndvi, out_color)
            # Save red-only hotspots overlay
            out_hot = proc_dir / f"ndvi_{date}_{tile}_hot.png"
            save_png_hot_overlay(ndvi, out_hot, hot_thresh)
            # Save true-color underlay if available
            out_rgb = None
            if "B03" in clipped and "B02" in clipped:
                g, _ = clipped["B03"]; b, _ = clipped["B02"]
                out_rgb = proc_dir / f"rgb_{date}_{tile}.png"
                save_png_rgb(red[0], g[0], b[0], out_rgb)
            # Compute bounds in EPSG:4326 (south, west, north, east)
            bounds_src = rasterio.transform.array_bounds(ndvi.shape[0], ndvi.shape[1], ndvi_prof["transform"])  # (minx,miny,maxx,maxy) in src CRS
            if "crs" in ndvi_prof and ndvi_prof["crs"] is not None:
                minx, miny, maxx, maxy = bounds_src
                west, south, east, north = transform_bounds(ndvi_prof["crs"], "EPSG:4326", minx, miny, maxx, maxy)
            else:
                # Fallback: empty bounds
                south = west = north = east = 0.0
            meta = {
                "file": out_png.name,
                "color": out_color.name,
                "hot": out_hot.name,
                "rgb": out_rgb.name if out_rgb else None,
                "tile": tile,
                "date": date,
                "bounds": [south, west, north, east],
                "mean": float(np.nanmean(ndvi)) if np.isnan(ndvi).sum() != ndvi.size else None,
            }
            with open(proc_dir / f"ndvi_{date}_{tile}.json", "w") as f:
                json.dump(meta, f)
            print(f"Saved {out_tif}, {out_png}, {out_color}, {out_hot}, {out_rgb} and metadata JSON")

    print("Done.")


def main():
    watch = os.environ.get("WATCH_JOBS", "0") == "1"
    if watch:
        jobs_dir = Path("/workspace/data/jobs")
        jobs_dir.mkdir(parents=True, exist_ok=True)
        print("[ingestor] Watching jobs in", jobs_dir)
        while True:
            jobs = sorted(jobs_dir.glob("*.json"))
            if not jobs:
                # sleep a bit
                import time
                time.sleep(3)
                continue
            job = jobs[0]
            ok = True
            try:
                with open(job, "r") as f:
                    j = json.load(f)
                bounds = j.get("bounds")  # [south, west, north, east]
                if not bounds or len(bounds) != 4:
                    print(f"[ingestor] Invalid job bounds in {job}")
                    # move to failed
                    failed_dir = jobs_dir / "failed"
                    failed_dir.mkdir(parents=True, exist_ok=True)
                    job.replace(failed_dir / job.name)
                    continue
                s, w, n, e = bounds
                geom = mapping(box(w, s, e, n))
                start = j.get("start", os.environ.get("START_DATE", "2023-06-01"))
                end = j.get("end", os.environ.get("END_DATE", "2023-08-31"))
                max_cloud = int(j.get("max_cloud", os.environ.get("MAX_CLOUD", "20")))
                limit = int(j.get("limit", os.environ.get("LIMIT", "4")))
                hot_thresh = float(j.get("hot_thresh", os.environ.get("HOT_NDVI_THRESH", "0.6")))
                print(f"[ingestor] Processing job {job.name} for {start}..{end} bounds={bounds}")
                process_geom(geom, start, end, max_cloud, limit, hot_thresh)
            except Exception as ex:
                print("[ingestor] Error processing job", job, ex)
                ok = False
            finally:
                # Move job to done/ or failed/ for simple status tracking
                try:
                    target_dir = jobs_dir / ("done" if ok else "failed")
                    target_dir.mkdir(parents=True, exist_ok=True)
                    job.replace(target_dir / job.name)
                except Exception:
                    # Fallback: attempt to unlink
                    try:
                        job.unlink(missing_ok=True)
                    except Exception:
                        pass
    else:
        aoi_path = Path(os.environ.get("AOI_PATH", "/workspace/data/aoi/lincoln_ne_aoi.geojson"))
        start = os.environ.get("START_DATE", "2023-06-01")
        end = os.environ.get("END_DATE", "2023-08-31")
        max_cloud = int(os.environ.get("MAX_CLOUD", "20"))
        limit = int(os.environ.get("LIMIT", "2"))
        hot_thresh = float(os.environ.get("HOT_NDVI_THRESH", "0.6"))
        geom = load_geom(aoi_path)
        process_geom(geom, start, end, max_cloud, limit, hot_thresh)


if __name__ == "__main__":
    main()
