Write-Host "Stopping existing containers..."
docker compose down

Write-Host "`nRebuilding API service (no cache)..."
docker compose build --no-cache api

Write-Host "`nStarting all services..."
docker compose up -d

Write-Host "`nStreaming API logs (Ctrl+C to exit)..."
docker logs -f matengine-api
