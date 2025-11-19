MAT Engine
====================================
A Python-based satellite analysis system that turns Sentinel-2 multispectral scenes into farmer-ready overlays, processed locally for privacy and reproducibility.

The repository mirrors the updated specification: deterministic ingest → preprocess → temporal SVD → overlay generation, a FastAPI backend, a React UI placeholder, and documentation tuned for humans *and* automation agents.

---

## Environment Setup ⚙️

**Python:** 3.10+ (tested on 3.11)

```bash
git clone https://github.com/hmeyer8/mat-engine.git
cd mat-engine
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.\.venv\Scripts\activate         # Windows PowerShell
pip install -r requirements.txt

# Optional GPU build (CUDA 12.1)

```

Copy `.env.example` → `.env` and fill in the blanks:

```env
MAT_DATA_DIR=./data
MAT_CACHE_DIR=./.cache
MAT_SAT_API_KEY=your-copernicus-token
COPERNICUS_USERNAME=...
COPERNICUS_PASSWORD=...
MAT_TILES_CACHE_DAYS=14
MAT_GPU_ENABLED=true
MAT_GPU_DEVICE=cuda:0
MAT_GPU_PRECISION=fp32
MAT_API_HOST=0.0.0.0
MAT_API_PORT=8080
MAT_API_CORS=http://localhost:5173
NEXT_PUBLIC_API_URL=http://localhost:8080
```

For the React UI, copy `ui/.env.example` → `ui/.env` and set `VITE_NEXT_PUBLIC_API_URL` (and optionally `VITE_MAPS_API_KEY`) so the dashboard points at the same FastAPI instance.

Each stage exposes a CLI (or a `make` target). Replace `demo-field` with a real identifier.

```bash
# 1) Ingest Sentinel-2 scenes (mock data today)
python -m src.ingest.run_ingest demo-field 68430 2022-01-01 2023-01-01

# 2) Preprocess: cloud mask, NDVI stack, tiling
python -m src.preprocessing.run_preprocessing demo-field --tile-size 64

# 3) Temporal SVD per tile stack
python -m src.temporal_svd.run_svd demo-field --rank 3

# 4) Aggregate into overlay + summary
python -m src.analysis.build_overlay demo-field

# Convenience target (runs all steps)
make FIELD=demo-field pipeline

# Serve API locally
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8080

# React UI dashboard
cd ui && npm install && npm run dev
```

Docker option:

```bash
docker compose up --build api
```

---

## FastAPI Endpoints & Schemas

| Method | Route | Description |
| ------ | ----- | ----------- |
| GET | `/health` | Service liveness |
| POST | `/fields` | Register field geometry/ZIP |
| GET | `/fields/{field_id}/summary` | Aggregated health metrics (runs analysis on demand) |
| GET | `/fields/{field_id}/overlay` | Streams PNG overlay |
| GET | `/fields/{field_id}/indices/ndvi` | NDVI temporal profile |
| GET | `/fields/{field_id}/svd/stats` | Singular values + explained variance |

**Input example** (`POST /fields`):

```json
{
	"field_id": "example123",
	"zip_code": "68430",
	"geometry": {
		"type": "Polygon",
		"coordinates": [[[ -96.75, 40.60 ], [ -96.74, 40.60 ], [ -96.74, 40.61 ], [ -96.75, 40.61 ], [ -96.75, 40.60 ]]]
	}
}
```

**Summary output**:

```json
{
	"field_id": "example123",
	"field_health_score": 0.83,
	"stress_label": "moderate",
	"overlay_path": "data/processed/example123/overlay.png",
	"svd_stats_path": "data/processed/example123/svd_stats.json"
}
```

**NDVI temporal profile**:

```json
{
	"field_id": "example123",
	"index": "ndvi",
	"temporal_profile": [0.62, 0.68, 0.71, 0.66],
	"latest": 0.66
}
```

---

## Backend ↔ UI Contract

- UI reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8080`).
- Overlay PNG fetched from `/fields/{field_id}/overlay` and draped on Google Maps via `MAPS_API_KEY`.
- Future endpoints (`/fields/{id}/tiles`, `/auth/*`) are documented for planning but not yet implemented.

---

## Data Placement & Naming

| Location | Contents | Notes |
|----------|----------|-------|
| `data/raw/<field_id>/` | SAFE/GeoTIFF scenes + `ingest_manifest.json` | Scenes named `S2A_<field>_<index>.tif` (example). |
| `data/processed/<field_id>/ndvi_stack.npz` | NDVI tensor `(T,H,W)` | Produced by preprocessing stage. |
| `data/processed/<field_id>/svd_stats.json` | `singular_values`, `explained_variance` | Feeds `/svd/stats`. |
| `data/processed/<field_id>/overlay.png` | RGB overlay | Color scale: green→yellow→orange→red. |

---

## GPU & Performance Notes

- CUDA 12.x drivers, cuDNN 9+, PyTorch installed via `pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision torchaudio`.
- Minimum hardware: RTX 3060 12 GB (or higher) for CNN workloads; current NDVI/SVD pipeline runs on CPU if `MAT_GPU_ENABLED=false`.
- Future PyO3/Rust accelerators will respect `MAT_GPU_ENABLED` and `MAT_GPU_DEVICE`.

---

## What’s Not Implemented Yet ❌

- CNN / ConvLSTM predictive models (heuristic only).
- Real Sentinel-2 downloads + cloud masking (ingest currently simulates metadata).
- Parcel search, ZIP-based UI, USDA CDL integration.
- Authentication, RBAC, or grower accounts.

Explicit non-goals keep the roadmap grounded.

---

## Task Map ✅

1. Implement real Sentinel-2 ingest (Copernicus + AWS mirrors).
2. Wire S2 Cloudless + multi-index preprocessing.
3. Tile generation + spatial joins with parcel boundaries.
4. Extend temporal alignment + SVD batching to multi-field workloads.
5. Export overlays as GeoTIFF/COG alongside PNG.
6. Build the React farmer dashboard (auth, ZIP lookup, parcel picker, overlay viewer).
7. Add authentication + secure storage.
8. Train baseline CNN/ConvLSTM models and expose inference endpoints.
9. Validate the entire pipeline on a demo ZIP code.

---

## Mathematical Appendix 🧮

Given a tile’s time-series matrix $\mathbf{X} \in \mathbb{R}^{T \times F}$:

$$\mathbf{X} = \mathbf{U}\mathbf{\Sigma}\mathbf{V}^\top$$

- $\mathbf{U}$ captures temporal modes (seasonality, stress onset).
- $\mathbf{\Sigma}$ ranks each mode by energy.
- $\mathbf{V}$ maps spectral contributions (bands/indices).

Low-rank approximation:

$$\mathbf{X}_k = \mathbf{U}_k \mathbf{\Sigma}_k \mathbf{V}_k^\top$$

Vegetation changes slowly, so a small $k$ captures most agronomic signal.

---

## Academic Foundations

- Jensen, J. R. *Introductory Digital Image Processing*. Pearson, 2015.
- Verrelst et al. “Optical remote sensing of vegetation traits.” *Remote Sensing of Environment*, 2015.
- Urbazaev et al. “SVD for Sentinel-2 vegetation time-series.” *IEEE JSTARS*, 2016.
- Rußwurm & Körner. “Temporal ConvLSTM for vegetation.” *ISPRS*, 2018.
- Féret et al. “Reflectance pattern dynamics.” *Remote Sensing of Environment*, 2019.
- Zhu & Woodcock. “Cloud detection for optical imagery.” *IEEE TGRS*, 2014.

---

## Future Work

- Integrate Landsat 8/9 for denser cadence.
- Ship CNN-based nitrogen/stress classifiers with TorchScript/ONNX exports.
- Historical grower reports + comparison charts.
- Offline “field kit” build for rugged laptops.
- Edge-device export for tractors/drones.

Built to be understandable, scientifically grounded, and farmer-first. If anything is unclear, open an issue and it will be clarified immediately.
9.2 Singular Value Decomposition

SVD decomposes the matrix:

X = U Σ Vᵀ


Interpretation:

U → temporal behavior

Σ → strength of temporal patterns

V → spectral structure

9.3 Low-Rank Approximation

A rank-k approximation is:

X_k = U_k Σ_k V_kᵀ


This filters noise and highlights meaningful vegetation changes.

9.4 Why It Works

Vegetation reflectance evolves gradually, making it well-suited to low-rank temporal modeling.

10. Future Work

Landsat-8/9 temporal enhancement

Deploy CNN stress classifiers

Historical trend reports

Local offline “field kit”

Edge-device support

Multi-field comparison views

11. Closing Notes

MAT Engine is designed to be:

Understandable

