from pathlib import Path
import argparse
import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.utils.logging import get_logger
from src.utils.paths import PROCESSED_DIR, MODELS_DIR


logger = get_logger("train")


def train(data_path: Path, model_path: Path) -> None:
    """Train a simple regression model and save it.

    Replace with your real model training code.
    """
    df = pd.read_csv(data_path)
    X = df[["x", "x2"]]
    y = df["y"]
    model = LinearRegression()
    model.fit(X, y)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    logger.info(f"Saved model to {model_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train model")
    parser.add_argument(
        "--data", type=str, default=str(PROCESSED_DIR / "data.csv"), help="Processed CSV"
    )
    parser.add_argument(
        "--model", type=str, default=str(MODELS_DIR / "model.pkl"), help="Model output path"
    )
    args = parser.parse_args()
    train(Path(args.data), Path(args.model))


if __name__ == "__main__":
    main()
