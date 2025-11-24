# MAT Engine UI (Next.js)

This directory is reserved for the public-facing Next.js Google Maps UI that consumes the MAT Engine API.

## Expected setup
- Place or clone the Next.js project here (e.g. `git clone git@github.com:hmeyer8/mat-engine-ui.git mat-engine-ui`).
- Ensure `.env.local` is populated with `NEXT_PUBLIC_API_URL="https://api.matengine.com"` (already included here).
- The UI should request cached tile JSON from the backend at `https://api.matengine.com/tiles` and post polygons to `https://api.matengine.com/analyze-field`.

## Build & deploy
```bash
npm install
npm run build
vercel deploy
```

Use the Vercel Hobby tier; no serverless functions are required.
