from pathlib import Path
import argparse
import pandas as pd

from src.utils.logging import get_logger
from src.utils.paths import RAW_DIR


logger = get_logger("ingest")


def ingest(output: Path) -> None:
    """Ingest data into the raw data folder.

    This demo writes a small synthetic dataset. Replace this with your
    actual download/fetch logic.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame({"x": [0, 1, 2, 3, 4], "y": [0, 1, 4, 9, 16]})
    df.to_csv(output, index=False)
    logger.info(f"Wrote raw data to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Data ingestion")
    parser.add_argument(
        "--output", type=str, default=str(RAW_DIR / "data.csv"), help="Output CSV path"
    )
    args = parser.parse_args()
    ingest(Path(args.output))


if __name__ == "__main__":
    main()
