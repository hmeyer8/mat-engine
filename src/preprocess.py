from pathlib import Path
import argparse
import pandas as pd

from src.utils.logging import get_logger
from src.utils.paths import RAW_DIR, PROCESSED_DIR


logger = get_logger("preprocess")


def preprocess(input_path: Path, output_path: Path) -> None:
    """Basic preprocessing/feature engineering demo.

    Adds a squared feature for demonstration, then writes to processed.
    """
    df = pd.read_csv(input_path)
    df["x2"] = df["x"] ** 2
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"Wrote processed data to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess data")
    parser.add_argument(
        "--input", type=str, default=str(RAW_DIR / "data.csv"), help="Input CSV path"
    )
    parser.add_argument(
        "--output", type=str, default=str(PROCESSED_DIR / "data.csv"), help="Output CSV path"
    )
    args = parser.parse_args()
    preprocess(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
