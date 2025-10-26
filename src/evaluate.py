from pathlib import Path
import argparse
import joblib
import pandas as pd
from sklearn.metrics import r2_score

from src.utils.logging import get_logger
from src.utils.paths import PROCESSED_DIR, MODELS_DIR


logger = get_logger("evaluate")


def evaluate(data_path: Path, model_path: Path) -> float:
    """Evaluate the trained model and print a metric."""
    df = pd.read_csv(data_path)
    X = df[["x", "x2"]]
    y = df["y"]

    model = joblib.load(model_path)
    y_pred = model.predict(X)
    score = r2_score(y, y_pred)
    logger.info(f"R2 score: {score:.4f}")
    return score


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate model")
    parser.add_argument(
        "--data", type=str, default=str(PROCESSED_DIR / "data.csv"), help="Processed CSV"
    )
    parser.add_argument(
        "--model", type=str, default=str(MODELS_DIR / "model.pkl"), help="Model path"
    )
    args = parser.parse_args()
    evaluate(Path(args.data), Path(args.model))


if __name__ == "__main__":
    main()
