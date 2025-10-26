from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path

from src.predict import load_model, predict
from src.utils.paths import MODELS_DIR


app = FastAPI(title="mat-engine API")


class PredictRequest(BaseModel):
    x: float


@app.on_event("startup")
def startup() -> None:
    global MODEL
    model_path = Path(MODELS_DIR / "model.pkl")
    MODEL = load_model(model_path) if model_path.exists() else None


@app.post("/predict")
def predict_endpoint(req: PredictRequest):
    if MODEL is None:
        return {"error": "Model not found. Train the model first."}
    y = predict(MODEL, req.x)
    return {"y": y}
