# MAT Engine Deployment Notes

## Backend (home GPU host)
- Build and run via Docker Compose:
  ```bash
  docker compose build api
  docker compose up -d
  ```
- .env must include `APP_ENV=production`, `PORT=8080`, `MAT_CACHE_DIR=/cache`.
- Cache volume is mounted from `./cache` → `/cache` in the container; Nebraska tiles live in `cache/tiles`.

## GitHub SSH + GHCR
- Generate key (if missing): `ssh-keygen -t ed25519 -C "hmeyer8@huskers.unl.edu"`.
- Start agent and add key:
  ```bash
  eval "$(ssh-agent -s)"
  ssh-add ~/.ssh/id_ed25519
  ```
- Test: `ssh -T git@github.com` then verify `git remote -v` uses SSH.
- Build/push image to GHCR:
  ```bash
  docker build -t ghcr.io/hmeyer8/mat-engine-api:latest .
  docker push ghcr.io/hmeyer8/mat-engine-api:latest
  ```
- Watchtower (in compose) polls GHCR every 30s and restarts the `matengine-api` container with `--cleanup`.

## Cloudflare Tunnel
1. Install: `curl -fsSL https://cli.cloudflare.com/install.sh | sudo bash`
2. `cloudflared tunnel login`
3. `cloudflared tunnel create matengine`
4. DNS: `cloudflared tunnel route dns matengine api.matengine.com`
5. Copy `cloudflared/config.yml` to `/etc/cloudflared/config.yml`
6. Enable: `sudo cloudflared service install && sudo systemctl enable --now cloudflared`

## Frontend (Vercel, Next.js)
- Clone UI into `mat-engine-ui/` and keep `.env.local` with `NEXT_PUBLIC_API_URL="https://api.matengine.com"`.
- Build/test locally: `npm install && npm run build`.
- Deploy: `vercel deploy` (Hobby, static only).

## Verification
- API ping: `curl https://api.matengine.com/api/ping`
- Tiles with bbox: `curl "https://api.matengine.com/tiles?bbox=-101,40.5,-95.5,42"`
- Analyze mock polygon:
  ```bash
  curl -X POST https://api.matengine.com/analyze-field \
    -H "Content-Type: application/json" \
    -d '{"field_id":"demo","polygon":{"type":"Polygon","coordinates":[[[-99.9,41.5],[-96.7,40.8],[-95.9,41.3],[-99.9,41.5]]]}}'
  ```
- UI builds: `npm install && npm run build` (in `mat-engine-ui` once populated) and `vercel deploy`.
