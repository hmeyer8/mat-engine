from pathlib import Path
import argparse

from src.ingest import ingest
from src.preprocess import preprocess
from src.train import train
from src.evaluate import evaluate
from src.utils.paths import RAW_DIR, PROCESSED_DIR, MODELS_DIR


def run_all() -> None:
    raw = RAW_DIR / "data.csv"
    processed = PROCESSED_DIR / "data.csv"
    model = MODELS_DIR / "model.pkl"

    ingest(raw)
    preprocess(raw, processed)
    train(processed, model)
    evaluate(processed, model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pipeline steps")
    parser.add_argument(
        "--steps",
        type=str,
        default="ingest,preprocess,train,evaluate",
        help="Comma-separated steps to run",
    )
    args = parser.parse_args()
    steps = [s.strip().lower() for s in args.steps.split(",")]

    raw = RAW_DIR / "data.csv"
    processed = PROCESSED_DIR / "data.csv"
    model = MODELS_DIR / "model.pkl"

    if "ingest" in steps:
        ingest(raw)
    if "preprocess" in steps:
        preprocess(raw, processed)
    if "train" in steps:
        train(processed, model)
    if "evaluate" in steps:
        evaluate(processed, model)


if __name__ == "__main__":
    main()
