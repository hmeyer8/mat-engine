# MAT Engine: Satellite‑Driven Nitrogen Intelligence Platform

Docker-first setup to run API, UI, PostGIS, and a Sentinel‑2 ingestor.

## Structure
```
mat-engine/
├── api/                      ← Spring Boot REST API
│   ├── src/main/java/com/matengine/api/web/PingController.java
│   ├── src/main/java/com/matengine/api/config/CorsConfig.java
│   └── src/main/resources/{ application.yml, db/migration/V1__init.sql }
├── ui/                       ← Next.js dashboard
│   ├── src/app/page.tsx
│   └── next.config.ts
├── ingestor/                 ← Python Sentinel‑2 ingestor (Planetary Computer)
│   ├── Dockerfile
│   └── ingest_s2.py
├── data/                     ← mounted volume for imagery
│   └── aoi/lincoln_ne_aoi.geojson
├── docker-compose.yml
├── .env.example
└── README.md
```

## Prerequisites
- Windows/macOS: Docker Desktop; Linux: Docker Engine + Compose
- Java 17+ and Node 18+ are not required if using Docker, but useful for local dev

## 1) Configure environment
```
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env -Force
```
Edit .env if desired (ports, dates, cloud threshold).

## 2) Build and run with Docker
```
docker compose build --no-cache
docker compose up -d db
# wait until db is healthy, then:
docker compose up -d api ui
```
Verify:
```
curl http://localhost:8080/api/ping
# {"message":"MAT Engine API running"}
open http://localhost:3001
```

## 3) Ingest Sentinel‑2 for Lincoln, NE
The ingestor clips bands to the AOI and computes NDVI, saving GeoTIFF + PNG preview into ./data.

```
# Ensure data/aoi/lincoln_ne_aoi.geojson exists (already included)
docker compose run --rm ingestor
# outputs go to: data/raw/sentinel-2/* and data/processed/sentinel-2/*
```

To change dates/clouds:
```
START_DATE=2023-05-01 END_DATE=2023-06-30 MAX_CLOUD=10 docker compose run --rm ingestor
```

## 4) View NDVI in the UI
- Open the dashboard at http://localhost:3000
- The top-right shows API status; the selector lists available NDVI previews
- Pick a preview to render the PNG served by the API from `data/processed/sentinel-2/`

Endpoints used by the UI:
- GET `http://localhost:8080/api/ndvi/list` → `[ { "file": "ndvi_YYYY-MM-DD_TILE.png", "tif": "..." }, ... ]`
- GET `http://localhost:8080/api/ndvi/image?file=ndvi_YYYY-MM-DD_TILE.png` → image/png stream

Tip: If the list is empty, run the ingestor first and refresh the page.

## Local development (optional)
- API (dev CORS): runs with SPRING_PROFILES_ACTIVE=dev and UI_ORIGIN from .env
- UI: uses ui/.env.local → NEXT_PUBLIC_API_URL=http://localhost:8080; UI runs on http://localhost:3001 by default (configurable via UI_PORT)

Commands:
```
# API
$env:SPRING_PROFILES_ACTIVE="dev"; $env:UI_ORIGIN="http://localhost:3000"; cd api; .\gradlew.bat bootRun
# UI
cd ui; npm install; npm run dev -- -p 3000
```

## CORS policy
- Dev (default): enabled only when `SPRING_PROFILES_ACTIVE=dev` to allow localhost UI origins (UI_ORIGIN env, default http://localhost:3001).
- Prod: prefer same-origin (reverse proxy). If cross-origin is required, set `UI_ORIGIN` to your UI domain and enable CORS for that profile.

## Troubleshooting
- Docker not running: start Docker Desktop (Windows/macOS) or systemd service (Linux).
- Port in use: free 3000/8080 (Windows: `netstat -ano | findstr :3000` → `taskkill /PID <PID> /F`).
- UI shows “Error connecting to API”: ensure API is up; NEXT_PUBLIC_API_URL in UI and CORS UI_ORIGIN match.
- DB migrations: API logs should show Flyway applying V1__init.sql; check `docker compose logs api`.

## Notes
- API reads PNGs from `./data/processed/sentinel-2/` mounted read-only at `/workspace/data` in the container.
- Ingestor writes to the same `./data` folder on the host, so outputs immediately become visible to the API and UI.

License: MIT