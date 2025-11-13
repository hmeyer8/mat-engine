# MAT Engine · Sentinel‑2 NDVI Analytics

End-to-end, Docker-first stack for ingesting Sentinel‑2 imagery and visualizing NDVI over fields with overlays, timeline, and a simple ingest-by-ZIP workflow.

## What you get

- API (Spring Boot): endpoints to search/list NDVI products, stream images, submit/poll ingest jobs by ZIP, and list processed fields.
- UI (Next.js + Leaflet): modern dashboard to submit a ZIP, watch job progress, and explore true-color underlay, NDVI color/hot overlays, and a timeline scrubber.
- Ingestor (Python): background worker that watches a jobs folder, pulls Sentinel‑2 via STAC/Planetary Computer, clips to AOI, computes NDVI, and writes sidecars + previews.

## Architecture

```
┌─────────┐       create job JSON         ┌───────────┐        watch/process        ┌──────────┐
│   UI    │ ───────────────────────────▶  │   API     │  ───────────────────────▶  │ Ingestor │
│ Next.js │        /api/ingest/zip        │ Spring    │     data/raw + processed   │  Python  │
└────┬────┘                                └────┬──────┘                            └────┬─────┘
		 │   poll status / search                  │        shared volume: ./data             │
		 ▼                                         ▼                                          ▼
	Map + overlays                      ./data/jobs, ./data/processed             PNG/TIF/JSON sidecars
```

Shared volume: `./data` (host) is mounted into API and Ingestor containers. API writes jobs; Ingestor reads jobs and outputs results used by the UI.

## Repository layout

```
mat-engine/
├─ api/            # Spring Boot REST API (controllers, config, Flyway migrations)
├─ ui/             # Next.js dashboard (Leaflet map, overlays, timeline)
├─ ingestor/       # Python NDVI worker (rasterio, shapely, pystac-client)
├─ data/           # Shared volume (jobs/raw/processed). Git-ignored except .gitkeep
├─ scripts/        # Helper scripts (optional)
├─ worker/         # Legacy/experimental (ignored)
├─ .env.example
├─ docker-compose.yml
└─ README.md
```

## Quick start

Prereqs: Docker Desktop (Windows/macOS) or Docker Engine + Compose (Linux).

1) Copy env and adjust if needed

```powershell
Copy-Item .env.example .env -Force
```

2) Start the stack

```powershell
docker compose up -d --build
```

3) Open the app

- UI: http://localhost:3000
- API: http://localhost:8080/api/ping

4) Try the ZIP workflow

- In the UI, enter a ZIP code (e.g., 68521) and submit.
- The API creates a job JSON under `./data/jobs`; the Ingestor processes it.
- The UI polls job status, then auto-loads new scenes and fits the map to the ZIP bounds.
- Use the scene selector and timeline to explore dates; toggle overlays (true-color, NDVI color, NDVI hot) and download previews.

Tip: If nothing shows, wait for the job to finish or check Ingestor logs.

## API surface (essentials)

- Health
	- GET `/api/ping` → `{ message: "..." }`
- NDVI
	- GET `/api/ndvi/list`
	- GET `/api/ndvi/search?south=&west=&north=&east=&start=&end=&limit=`
	- GET `/api/ndvi/image?file=...` (streams PNG)
- Fields
	- GET `/api/fields/list` (aggregates unique field bounds from sidecars)
- Ingest by ZIP
	- GET `/api/ingest/zip?zip=68521` → `{ jobId, bounds, start, end }`
	- GET `/api/ingest/status?jobId=...` → `{ jobId, status, job? }`
	- GET `/api/ingest/jobs` → `{ pending:[], done:[], failed:[] }`

## Data layout

```
data/
├─ jobs/             # Job JSONs (API writes; Ingestor moves to done/failed)
├─ raw/sentinel-2/   # Band GeoTIFFs (B02/B03/B04/B08) by date/tile
└─ processed/sentinel-2/
	 ├─ ndvi_YYYY-MM-DD_TILE.tif           # NDVI GeoTIFF (EPSG retained)
	 ├─ ndvi_YYYY-MM-DD_TILE.png           # NDVI preview (grayscale)
	 ├─ color_YYYY-MM-DD_TILE.png          # NDVI colorized overlay
	 ├─ hot_YYYY-MM-DD_TILE.png            # NDVI hotspot overlay (darker red = stronger)
	 ├─ rgb_YYYY-MM-DD_TILE.png            # True-color underlay
	 └─ ndvi_YYYY-MM-DD_TILE.json          # Sidecar: bounds (EPSG:4326), date, tile, mean, paths
```

Git hygiene: `data/` is ignored in Git except for small `.gitkeep` files that preserve structure; logs and build outputs are also ignored. Only source/config changes are meant to be committed.

## Configuration notes

- `.env` (root): ports, profile, and any service-level settings. See `.env.example`.
- `ui/.env.local` (optional): override `NEXT_PUBLIC_API_URL` if needed; UI defaults to `http://localhost:8080`.
- Volumes: API must have write access to `/workspace/data/jobs`; Ingestor uses `/workspace/data` read/write.

## Development (optional)

- API (Windows PowerShell):
```powershell
cd api
./gradlew.bat bootRun
```

- UI:
```powershell
cd ui
npm install
npm run dev -- -p 3000
```

The Docker workflow is recommended for consistency; the above is only for local iteration.

## Troubleshooting

- API 500 on `/api/ingest/zip`: likely a read-only volume for `./data/jobs`. Ensure docker-compose mounts `./data/jobs` read-write into the API container.
- UI stuck at "Processing imagery…": job may still be running; the UI completes when `/api/ingest/status` → `done`. Check `docker compose logs -f ingestor`.
- Map shows nothing: the UI hides the map until a ZIP is submitted; after completion, the viewport is constrained to the ZIP bounds.
- Huge Git diff: `.gitignore` excludes `data/**`, logs, and build outputs. If you see large data files staged, regenerate your `.gitignore` from this repo and run `git restore --staged <files>`.

## License

MIT