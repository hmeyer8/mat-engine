"""CLI entrypoint for ingesting Sentinel-2 scenes."""
from __future__ import annotations

import argparse
import random
from datetime import datetime

from src.utils.io import save_json
from src.utils.logger import get_logger
from src.utils.paths import field_raw_dir

logger = get_logger(__name__)


def run_ingest(field_id: str, zip_code: str, start: str, end: str) -> str:
    """Simulate downloading scenes by writing metadata files."""
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    scenes = []
    seed = hash((field_id, zip_code, start, end)) & 0xFFFF
    rng = random.Random(seed)
    days = (end_dt - start_dt).days or 1
    for idx in range(min(5, days)):
        capture = start_dt + (end_dt - start_dt) * (idx / max(1, days))
        scenes.append(
            {
                "scene_id": f"S2A_{field_id}_{idx:02d}",
                "capture_ts": capture.isoformat(),
                "cloud_cover": round(rng.uniform(0, 0.4), 3),
                "zip_code": zip_code,
            }
        )
    payload = {
        "field_id": field_id,
        "zip_code": zip_code,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "scenes": scenes,
        "notes": "Simulated ingest metadata. Replace with real Sentinel-2 fetch logic.",
    }
    raw_dir = field_raw_dir(field_id)
    path = raw_dir / "ingest_manifest.json"
    save_json(path, payload)
    logger.info("Wrote ingest manifest to %s", path)
    return str(path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Sentinel-2 data for a field")
    parser.add_argument("field_id", type=str, help="Field identifier")
    parser.add_argument("zip_code", type=str, help="US ZIP code")
    parser.add_argument("start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("end", type=str, help="End date (YYYY-MM-DD)")
    return parser.parse_args()


def main() -> None:  # pragma: no cover - CLI wrapper
    args = _parse_args()
    run_ingest(args.field_id, args.zip_code, args.start, args.end)


if __name__ == "__main__":
    main()
