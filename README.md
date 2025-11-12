# MAT Engine: Satellite‑Driven Nitrogen Intelligence Platform

MAT Engine is a geospatial machine learning system that models crop health and predicts nitrogen deficiencies from Sentinel‑2 imagery. It includes:
- A Spring Boot API for services and orchestration
- A Next.js UI for visualization
- (Optional) Python components for data/ML workflows

## Project Architecture
```
mat-engine/
├── api/                      ← Spring Boot REST API
│   ├── src/main/java/com/matengine/api/
│   │   ├── web/PingController.java
│   │   └── config/CorsConfig.java     ← dev-only CORS
│   └── src/main/resources/application.yml
├── ui/                       ← Next.js app (dashboard)
│   ├── src/app/page.tsx
│   └── next.config.ts
├── data/                     ← optional: local data workspace (git-ignored)
│   ├── raw/
│   └── processed/
├── models/                   ← optional: model artifacts (git-ignored)
├── .env                      ← local env (not committed)
├── .env.example              ← example env for contributors
└── README.md
```

## Prerequisites
- Windows 10/11
- Java 17+, Node.js 18+, Git
- Optional: Docker Desktop (for compose)

## Quickstart (Local Dev)

1) Configure environment
- Copy `.env.example` → `.env` and adjust if needed:
  - API_PORT=8080
  - UI_ORIGIN=http://localhost:3000
  - NEXT_PUBLIC_API_URL=http://localhost:8080

For the UI:
- Create `ui/.env.local` (already present):
```
NEXT_PUBLIC_API_URL=http://localhost:8080
```

2) Run the API
```
# PowerShell
$env:SPRING_PROFILES_ACTIVE = "dev"
$env:UI_ORIGIN = "http://localhost:3000,http://localhost:3001"
$env:API_PORT = "8080"
cd api
.\gradlew.bat bootRun
```
Verify:
```
curl http://localhost:8080/api/ping
# {"message":"MAT Engine API running"}
curl http://localhost:8080/actuator/health
```

3) Run the UI
```
cd ui
npm install
npm run dev -- -p 3000
# open http://localhost:3000
```

## Run with Docker (optional)
Ensure Docker Desktop is running.
```
docker compose build
docker compose up -d
# UI:  http://localhost:3000
# API: http://localhost:8080/api/ping
```

## Configuration
- API_PORT: port the Spring API listens on (default 8080)
- UI_ORIGIN: allowed browser origins (CORS). Comma‑separated for dev, e.g. `http://localhost:3000,http://localhost:3001`
- NEXT_PUBLIC_API_URL: base URL the UI calls, e.g. `http://localhost:8080`

## API Endpoints
- GET `/api/ping` → health message
- GET `/actuator/health` → liveness/readiness

## Troubleshooting
- UI shows “Error connecting to API”
  - Verify API is up: `curl http://localhost:8080/api/ping`
  - Confirm UI env: `ui/.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8080`
  - Free port 3000: `netstat -ano | findstr :3000` → `taskkill /PID <PID> /F`
  - Ensure CORS includes your UI port via `UI_ORIGIN`
- Next.js warns about workspace root
  - Already pinned in `ui/next.config.ts`
- Avoid committing build output
  - Ensure `.gitignore` excludes `api/bin`, `build`, and `ui/.next`

## License
MIT