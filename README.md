Comparing CNN vs. Temporal SVD for Early Nitrogen Deficiency Detection (Nebraska)
===============================================================================
Goal: use Sentinel-2 multispectral time series to warn farmers about likely nitrogen (N) deficiency ~7 days before visible symptoms, and compare two approaches side by side:

- CNN (spatial–spectral–temporal deep learning): learn textures + spectral shifts (e.g., red-edge drop, greener visible bands from chlorophyll loss), with options for 3D/temporal CNN or CNN+LSTM; explore Fourier-style convolutions for efficiency.
- Temporal SVD (linear low-rank analysis): PCA/SVD on multi-date indices to extract dominant growth patterns and anomaly components that flag early N stress; use lightweight classifiers or thresholds on principal component scores.

This repository is the working codebase for that comparison: deterministic ingest, preprocessing, temporal SVD, a starter CNN scorer, a FastAPI backend, and a React/Vite UI for visualization.

What we will do
---------------
- Assemble Sentinel-2 time series (10–20 m, ~5-day revisit) for Nebraska crops; compute NDVI, NDRE, and chlorophyll-sensitive indices.
- Train/benchmark two predictors:
  - CNN pathway: patch-based CNN with temporal context (stacked dates or CNN+LSTM); experiment with Fourier convolutions for speed.
  - SVD pathway: temporal PCA/SVD over indices to capture healthy growth vs. anomaly modes; simple classifier or threshold for “deficiency in ~7 days”.
- Compare accuracy, early-warning lead time, compute cost, and interpretability; visualize saliency/attention for CNN and principal components for SVD.
- Deliver an end-to-end demo: ingest -> preprocess -> SVD stats -> (optional) CNN inference -> overlay + NDVI timeline in the UI.

Hardware & assumptions
----------------------
- Target dev box: Core i5-13KF CPU, RTX 4060 GPU, 2 TB SSD.
- Python 3.10+; Node 18+ for the UI.
- Real Sentinel-2 access via Copernicus Data Space (set `CDSE_CLIENT_ID`/`CDSE_CLIENT_SECRET`). If missing, the pipeline can fall back to simulated data for demos.

Setup
-----
```bash
git clone https://github.com/hmeyer8/mat-engine.git
cd mat-engine

python -m venv .venv
.\.venv\Scripts\activate        # Windows PowerShell
source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt

# Optional GPU wheels (CUDA 12.1)
pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio
```

Environment files
-----------------
Copy the examples and fill secrets:
```bash
cp .env.example .env
cp ui/.env.example ui/.env
```
Key vars:
- `MAT_DATA_DIR`, `MAT_CACHE_DIR`: where raw/processed data live.
- `CDSE_CLIENT_ID`, `CDSE_CLIENT_SECRET`: Copernicus API access.
- `MAT_GPU_ENABLED`, `MAT_GPU_DEVICE`: enable GPU.
- `NEXT_PUBLIC_API_URL` / `VITE_NEXT_PUBLIC_API_URL` (UI) should point at the FastAPI host (default `http://localhost:8080`).
- `VITE_MAPS_API_KEY` is required for the Google Maps JavaScript SDK used by the dashboard. Generate a browser key in Google Cloud (Maps JavaScript API + Data Layer enabled) and place it in `ui/.env`.

Field boundaries for the UI live in `ui/public/geojson/fields.geojson`. Drop in your own GeoJSON polygons (one feature per field) and reload the Vite dev server to see them in the map picker, or use the new "Load farmland in map" control (see below) to fetch OpenStreetMap parcels on demand.

Pipeline commands (replace ids/dates as needed)
-----------------------------------------------
```bash
# Ingest Sentinel-2 scenes (or simulated) for a field/ZIP/date range
python -m src.pipeline ingest demo-field 68430 2022-01-01 2023-01-01

# Precompute indices/tiles
python -m src.pipeline preprocess demo-field --tile-size 64

# Temporal SVD (stats + components)
python -m src.pipeline svd demo-field --rank 3

# Analysis stage (overlays, scores)
python -m src.pipeline analyze demo-field --rank 3

# End-to-end
python -m src.pipeline pipeline demo-field 68430 2022-01-01 2023-01-01 --rank 3

# Makefile shortcut
make FIELD=demo-field pipeline
```

Run services
------------
```bash
# API
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8080

# UI
cd ui
npm install
npm run dev
```
Open the dashboard, point it at `NEXT_PUBLIC_API_URL`, and load `demo-field` (or your field id) to see overlay + NDVI timeline; SVD stats show explained variance and singular values.

Interactive Google Maps dashboard
---------------------------------
- **Field selection:** The UI now boots with a Google Maps Data Layer that reads `ui/public/geojson/fields.geojson`. Click any polygon to highlight it, inspect crop metadata, and push the selected `field_id` into the analytics workflow.
- **Dynamic parcels for Nebraska:** Pan/zoom over Nebraska and press **Load farmland in map** to call `GET /api/fields/osm`. The backend proxies the Overpass API, converts farmland ways/relations into feature-rich GeoJSON, and streams them to the browser so you can select any parcel in view. Optional crop filters narrow the query (`corn`, `soybean`, etc.).
- **Sentinel-2 date picker:** After a selection, the client calls `/api/available_dates?field_id=<id>` (or falls back to placeholder dates) to populate a dropdown of cloud-free scenes. Pick a date, then trigger analysis.
- **Heatmap overlays:** Toggle CNN and SVD overlays to project either `fields/<id>/overlay` or `/fields/<id>/svd/overlay` PNGs directly onto the map via `google.maps.GroundOverlay`. Bounds are derived from the GeoJSON polygon, so the imagery snaps to each field footprint.
- **Field analytics popup:** Clicking **Analyze field** now queues a background job (`POST /api/jobs`), polls `/api/jobs/<id>` for status, and fetches `/api/analysis/<field_id>` once the pipeline is done. The info window updates with severity, trend, confidence, and recommendations while the side panel mirrors the same summary plus model metrics.
- **Manual entry still works:** The classic `FieldSelector` form remains alongside the map so you can paste an ID or run scripted scenarios.

If `/api/available_dates`, `/api/jobs`, or `/api/analysis/<field_id>` are not yet implemented in your FastAPI app, the UI injects deterministic placeholder dates/insights so the map remains usable while you finish the backend.

New API surface (FastAPI)
-------------------------
- `GET /api/fields/osm?bbox=<south,west,north,east>&crop=corn` → Returns a GeoJSON FeatureCollection assembled from the OpenStreetMap Overpass API. The UI passes the current map bounds, making it easy to browse any Nebraska parcel without pre-baking shapefiles.
- `GET /api/available_dates?field_id=<id>` → `{ field_id, dates: ["2025-06-05", ...] }`
  - Intended to query Sentinel-2 metadata (Copernicus, Sentinel Hub, etc.) for the footprints represented in the GeoJSON file.
  - Stub behaviour: return recent weekly dates until the real catalog integration is wired up.
- `POST /api/jobs` with `{ field_id, start_date, end_date, geometry, zip_code?, source? }`
  - Persists the polygon/metadata, writes a job record under `data/jobs`, and schedules the full pipeline (ingest → preprocess → SVD → CNN overlay) in a background task.
- `GET /api/jobs/<job_id>` → `{ job_id, status, message, result? }` so the UI can poll until the worker flips from `queued`/`running` to `succeeded` or `failed`.
- `GET /api/analysis/<field_id>` → Returns the latest summary assembled from `analysis_summary.json`, including overlay URLs, CNN/SVD metrics, and recommendations shown in the dashboard panel.

Both endpoints are thin orchestration layers on top of the existing `src/pipeline.py` steps. Keep model/preprocessing code in dedicated modules so these routes remain declarative and testable.

How we will compare CNN vs. SVD
-------------------------------
- **Data**: Sentinel-2 bands or derived indices (NDVI, NDRE, chlorophyll index) over time; field polygons for Nebraska crops.
- **CNN path**: patch inputs with stacked dates; baseline CNN/LSTM; optional Fourier-style conv for efficiency; outputs “N deficiency likely in 7 days” + confidence. Visualize attention/saliency.
- **SVD path**: temporal matrices (time x indices or time x pixels) -> SVD -> top components; threshold or small classifier on PC scores for early warning. Plot PCs to explain stress patterns.
- **Metrics**: early-warning lead time, precision/recall/AUC, inference time, GPU/CPU cost, interpretability artifacts.
- **Hybrid idea**: use SVD for denoising/compression then a compact CNN/MLP; or SVD to flag anomalies then CNN to confirm.

Repository map (high level)
---------------------------
- `src/` – pipeline, ingest, preprocessing, SVD, API.
- `ui/` – React/Vite dashboard.
- `docs/` – architecture and playbooks.
- `data/` – raw/processed data (gitignored).
- `scripts/` – helper tooling (e.g., reports).

Roadmap (near term)
-------------------
- Wire real Sentinel-2 ingest (Copernicus + masks) and multi-index preprocessing.
- Baseline temporal CNN/LSTM training on Nebraska plots; add Fourier conv experiment.
- Harden temporal SVD + classifier for anomaly alerts; export PC visualizations.
- Benchmark both paths on shared datasets (accuracy, lead time, cost); document results.
- Polish UI: map overlays, side-by-side CNN vs. SVD signals, downloadables for farmers.

If anything is unclear or out of date, open an issue and we will align the docs and code.
