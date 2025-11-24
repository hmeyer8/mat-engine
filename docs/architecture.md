# MAT Engine Architecture Plan

This document captures the target state requested in the updated README so we can align the repository accordingly.

## Directory Layout (Target)
```
mat-engine/
├── data/
│   ├── raw/
│   └── processed/
├── docs/
├── notebooks/
├── src/
│   ├── api/
│   ├── models/
│   ├── utils/
│   └── pipeline.py
├── tests/
├── ui/
├── requirements.txt
├── docker-compose.yml
├── Makefile
└── README.md
```

## Language Split
- **Python** for ingest, preprocessing, modeling, FastAPI backend, and pipeline orchestration.
- **JavaScript/TypeScript (React)** only within `ui/` for the farmer dashboard (thin client hitting the FastAPI endpoints).
- **Rust** reserved for future performance-critical kernels; exported via PyO3 wheels and invoked from Python modules.

Existing sub-projects (`api/`, `mat-engine-ui/`, `ml-worker/`, `rust-core/`) are superseded by this structure and will be removed to avoid confusion.

## Pipeline Phases
1. `src/pipeline.py` – ingest → preprocess → temporal SVD → overlay + CNN fusion (single orchestration point).
2. `src/models` – inference-ready abstractions (baseline heuristic now, PyTorch later).
6. `src/api` – FastAPI service exposing summaries/overlays/indices endpoints.
7. `src/utils` – shared helpers (raster IO, geometry, configuration).

## Execution Flow
- A single CLI (`python -m src.pipeline <command>`) fronts ingest, preprocessing, SVD, analysis, and the end-to-end pipeline so orchestration stays in one place.
- All heavy compute steps will be GPU-aware and configured through a `.env` file documented in the README.

## Data & Naming Conventions
- Raw Sentinel-2 scenes stored as SAFE archives or GeoTIFFs inside `data/raw/<field_id>/<scene-id>.tif`.
- Processed tiles/overlays land in `data/processed/<field_id>/...` with naming patterns described in the README.
- Model artifacts saved under `models/` (later under `artifacts/` if needed) but tracked explicitly.

## API Surface
FastAPI endpoints:
- `GET /health`
- `GET /fields/{field_id}/summary`
- `GET /fields/{field_id}/overlay`
- `GET /fields/{field_id}/indices/{index_name}` (e.g., ndvi, ndre)
- `GET /fields/{field_id}/svd/stats`
- `POST /fields` for registering a new field + geometry

Each endpoint returns JSON schemas that are documented in the README.

## UI Integration
The React UI is served separately via `ui/`. It communicates with the FastAPI backend using `NEXT_PUBLIC_API_URL`. Sample requests and environment variables will be documented.

## Next Actions
1. Remove legacy sub-projects to reduce clutter.
2. Scaffold the Python modules with runnable stubs + baseline heuristic model.
3. Update README with environment setup, GPU requirements, data links, pipeline commands, schemas, and task map.
4. Provide tests validating preprocessing helpers and API endpoints.
5. Add Makefile targets and docker-compose definitions to streamline local runs.
