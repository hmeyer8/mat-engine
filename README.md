# mat-engine

Modern, reproducible ML project structure with clear separation of concerns and a tiny working pipeline + API scaffold.

## Project layout

```
mat-engine/
├── data/
│   ├── raw/              ← unprocessed data
│   └── processed/        ← cleaned, labeled data
├── src/                  ← ALL your source code lives here
│   ├── ingest.py         ← data ingestion logic (download, fetch, etc.)
│   ├── preprocess.py     ← data cleaning & feature extraction
│   ├── train.py          ← model training code
│   ├── evaluate.py       ← model validation & metrics
│   ├── predict.py        ← inference helpers
│   ├── pipeline.py       ← orchestration script tying it all together
│   └── utils/            ← helper functions (logging, paths)
├── models/               ← trained model artifacts (gitignored)
├── app/
│   └── main.py           ← FastAPI app for deployment
├── Dockerfile
├── dvc.yaml              ← optional (DVC pipeline wiring)
├── requirements.txt
└── README.md
```

Note: The diagram you shared used `mat_engine/` as the repo root; here the repo is named `mat-engine`, but the structure is equivalent.

## Quickstart (Windows PowerShell)

Set up a virtual environment and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the end-to-end pipeline (ingest → preprocess → train → evaluate):

```powershell
python -m src.pipeline
# or run specific steps
python -m src.pipeline --steps ingest,preprocess
```

Start the API (after training creates `models/model.pkl`):

```powershell
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs for interactive Swagger UI.

## Optional: DVC workflow

Initialize DVC (one time) and reproduce the pipeline:

```powershell
dvc init
dvc repro
```

## Notes

- Data and model artifacts are gitignored by default; `.gitkeep` files keep directories in Git.
- Replace the demo logic in `src/*.py` with your real code as you iterate.
- The Dockerfile provides a minimal FastAPI serving image; adjust as needed for GPUs, etc.