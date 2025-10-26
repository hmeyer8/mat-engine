from pathlib import Path
import joblib
import numpy as np

from src.utils.paths import MODELS_DIR


def load_model(model_path: Path | None = None):
    model_path = model_path or (MODELS_DIR / "model.pkl")
    return joblib.load(model_path)


def predict(model, x: float) -> float:
    arr = np.array([[x, x ** 2]])
    return float(model.predict(arr)[0])
