
# MAT Engine: Satellite-Driven Nitrogen Intelligence Platform

**Meyer AgTech Engine (MAT Engine)** is a geospatial machine learning system designed to model crop health and predict nitrogen deficiencies from **Sentinel-2 multispectral imagery**.  
It integrates modern data engineering practices, spatiotemporal deep learning, and geospatial visualization to transform open satellite data into actionable agronomic insights.

---

## Overview

MAT Engine is built to support **precision agriculture at scale**.  
It leverages publicly available Earth observation data to:
- Quantify crop vigor through vegetation indices (NDVI, NDRE, GNDVI)  
- Detect and forecast **nitrogen stress** at sub-field resolution  
- Provide interpretable, map-based recommendations for agronomists and growers  

All model development is conducted locally on a high-performance workstation equipped with an **Intel i5-13600KF** and **RTX 4060 (8 GB)** GPU, with future migration planned to **cloud-based distributed training** (AWS SageMaker / Vertex AI).

---

## Experimental Region

Initial prototyping and model validation focus on a **2 mi² test area** centered at:

> **40°56′42.9″ N, 97°55′17.9″ W**  
> Selected for its representative crop diversity and spectral separability.

---

## Project Architecture

```
mat-engine/
├── data/
│   ├── raw/              ← unprocessed Sentinel-2 scenes
│   └── processed/        ← cloud-masked, tiled, and labeled NDVI datasets
├── src/
│   ├── ingest.py         ← satellite data acquisition (SentinelHub / eo-learn)
│   ├── preprocess.py     ← cloud masking, vegetation index computation, tiling
│   ├── train.py          ← GPU-accelerated training (ResNet, ConvLSTM, U-Net)
│   ├── evaluate.py       ← validation, cross-region metrics, and explainability
│   ├── predict.py        ← batch inference and visualization utilities
│   ├── pipeline.py       ← orchestrates full pipeline (ingest → train → evaluate)
│   └── utils/            ← configuration, logging, and I/O helpers
├── models/               ← serialized checkpoints and artifacts (git-ignored)
├── app/
│   └── main.py           ← FastAPI service for model inference and API delivery
├── Dockerfile            ← GPU-ready image for deployment
├── requirements.txt
├── dvc.yaml              ← optional: DVC data-versioning pipeline
└── README.md
```

---

## Getting Started (Windows / PowerShell)

### 1) Environment setup
```powershell
python -m venv .venv
\.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Execute the ML pipeline
```powershell
python -m src.pipeline
# or run specific stages
python -m src.pipeline --steps ingest,preprocess,train
```

### 3) Launch the local API
```powershell
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs for the interactive Swagger UI.

## Model Development
The current baseline leverages ResNet-18 pretrained on ImageNet, fine-tuned on Sentinel-2 NDVI composites. Future iterations will incorporate:

| Phase | Model                       | Objective                                 |
|------:|-----------------------------|-------------------------------------------|
|     1 | ResNet-18 / EfficientNet-B0 | Baseline spatial nitrogen classification  |
|     2 | ConvLSTM / Temporal CNN     | Multi-date NDVI time-series forecasting   |
|     3 | U-Net / DeepLabV3+          | Sub-field nitrogen stress segmentation    |
|     4 | Vision Transformer (ViT)    | Global-context spatial–temporal modeling  |

All training utilizes mixed precision (FP16) and gradient scaling for maximal GPU efficiency.
Evaluation includes R², RMSE, F1, and IoU metrics, alongside Grad-CAM visual attribution for interpretability.

## Data Processing Standards
- Acquisition: Sentinel-2 L2A imagery via SentinelHub or Google Earth Engine
- Cloud masking: `s2cloudless` + morphological filtering
- Index derivation: `NDVI = (B8 − B4) / (B8 + B4)`; `NDRE = (B8 − B5) / (B8 + B5)`
- Tiling: 128–256 px patches aligned to field boundaries
- Normalization: Per-band standardization and temporal stacking

All preprocessing steps are reproducible through version-controlled scripts and DVC integration.

## MLOps & Reproducibility
- Experiment tracking: MLflow / Weights & Biases
- Data versioning: DVC + Git LFS (optional)
- Containerization: Docker (GPU base image)
- Future integration: AWS S3 + SageMaker training pipelines


Citation
If referencing this work in academic or industrial contexts:

Meyer, H. (2025). MAT Engine: Satellite-Driven Nitrogen Intelligence Platform.
Lincoln Air National Guard / University of Nebraska – Lincoln.
https://github.com/hmeyer8/mat-engine

Vision
“The goal of MAT Engine is to make high-resolution, nitrogen-aware crop intelligence accessible to every farmer—leveraging open satellite data, modern AI, and transparent science.”