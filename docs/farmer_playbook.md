# Farmer Playbook

This playbook explains how growers and agronomists interact with the *hosted* MAT Engine experience. Farmers never touch Git, Docker, or GPUs; they simply log into your website. All heavy processing stays on your home GPU rig behind the scenes.

---

## 1. Roles at a Glance

| Role | Responsibilities | Tools |
| ---- | ---------------- | ----- |
| **Farmer / Agronomist** | Log into the MAT dashboard, request or view fields, read NDVI summaries, download overlays. | Browser (desktop/tablet) pointing to `https://app.mat-engine.example.com`. |
| **Operator (you)** | Keep the pipeline running on the home PC/GPU, publish fresh overlays to the cloud app, and respond to support tickets. | Local MAT Engine repo + GPU workstation. |

---

## 2. Farmer Experience (What They See)
1. **Sign-in link** – Share a short URL (e.g., `https://matengine.ag`) plus temporary credentials.
2. **Field selector** – Growers choose a field ID that you pre-provisioned; they can search by name or ZIP.
3. **Dashboard panels** – They see the NDVI timeline, stress overlay, SVD panel, and summary cards pulled from your published data.
4. **Exports** – Farmers download overlay PNGs or PDF briefs you’ve generated—no local installs required.

> Tip: Embed a feedback button in the UI that emails support@matengine.ag; growers never wait for you to text back.

---

## 3. Operator Runbook (What You Do at Home)
1. **Refresh data** – On the GPU workstation run:
   ```powershell
   make FIELD=<field_id> ZIP=<zip> pipeline
   python scripts/farmer_report.py <field_id>
   ```
   This recomputes NDVI stacks and writes `overlay.png`, `analysis_summary.json`, `svd_stats.json`, and `report.md` under `data/processed/<field_id>/`.
2. **Publish to the cloud site** – Sync the processed folder to your hosting bucket or server (e.g., `aws s3 sync data/processed/<field_id> s3://matengine-prod/fields/<field_id>`). The website reads directly from that bucket.
3. **Update catalog** – Insert the latest metadata (date range, health score, overlay URL) into the hosted API/database so the UI lists the refreshed field.
4. **Notify farmers** – Send an automated email or SMS via your CRM letting the grower know a new overlay is live.

Everything above happens on your PC—farmers only receive polished results in their browser.

---

## 4. Deployment Topology
- **Home GPU rig**: Runs ingest → preprocess → SVD → overlay. Uses the `.env` and Makefile shipped in this repo.
- **Cloud API**: FastAPI container deployed to your VPS/cloud account with read-only access to the published `data/processed` artifacts.
- **Cloud UI**: Vite/React build served via your CDN. Environment var `VITE_NEXT_PUBLIC_API_URL` points at the hosted API.
- **Storage bridge**: S3 bucket, Azure Blob, or simple SFTP share where you upload the generated PNG/JSON/NDVI stacks for the cloud services to consume.

This separation lets you iterate locally without exposing the GPU box to the public internet while still giving farmers instant access.

---

## 5. Farmer-Facing Support Checklist
- [ ] Field appears in dashboard list
- [ ] Overlay timestamp matches latest run
- [ ] NDVI timeline shows at least 4 observations
- [ ] Recommendation text (from `report.md`) was copied into the UI
- [ ] Download button returns a valid PNG/PDF
- [ ] Support link routes to your help inbox

Run through the checklist before inviting a grower to the site.

---

## 6. Troubleshooting (Farmer View)
| Symptom | Farmer Message | Operator Fix |
| ------- | -------------- | ------------ |
| Field missing | “Field not yet published. Please contact support.” | Verify you synced `analysis_summary.json` + catalog entry. |
| Overlay blank | “Overlay still rendering, check back in 5 minutes.” | Ensure `overlay.png` uploaded and CDN cache cleared. |
| Timeline stale | “Latest NDVI date: <date>. New run scheduled.” | Re-run pipeline locally and redeploy JSON stack. |
| Login issue | “Use reset link or text support.” | Reset password/token in auth provider. |

---

## 7. Roadmap Items Farmers Care About
- Automated emails when a new overlay posts.
- ZIP search + parcel base layers in the hosted UI.
- Mobile-ready PDF reports with your logo.
- Historical comparisons (e.g., “this week vs last year”).
- Shared links per field so co-ops can view without full accounts.

Keep this playbook in lockstep with what you host publicly—no farmer ever needs local installs, only their browser.
