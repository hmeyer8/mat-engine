"""Generate a farmer-friendly snapshot for a processed field."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Sequence

import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils.io import load_json
from src.utils.paths import field_processed_dir, field_raw_dir

console = Console()


def _load_summary(field_id: str) -> dict:
    summary_path = field_processed_dir(field_id) / "analysis_summary.json"
    if not summary_path.exists():
        raise SystemExit(
            "analysis_summary.json is missing. Run the pipeline before creating a report."
        )
    return load_json(summary_path)


def _load_svd(field_id: str) -> dict:
    path = field_processed_dir(field_id) / "svd_stats.json"
    if not path.exists():
        raise SystemExit("svd_stats.json is missing. Run the temporal SVD stage first.")
    return load_json(path)


def _load_ndvi_profile(field_id: str) -> np.ndarray:
    ndvi_path = field_processed_dir(field_id) / "ndvi_stack.npz"
    if not ndvi_path.exists():
        raise SystemExit("ndvi_stack.npz is missing. Run preprocessing to create it.")
    stack = np.load(ndvi_path)["ndvi"]
    return stack.mean(axis=(1, 2))


def _load_manifest_dates(field_id: str) -> List[str]:
    manifest_path = field_raw_dir(field_id) / "ingest_manifest.json"
    if not manifest_path.exists():
        return []
    manifest = load_json(manifest_path)
    scenes = manifest.get("scenes", [])
    return [scene.get("capture_ts", "") for scene in scenes]


def _trend_descriptor(profile: Sequence[float]) -> float:
    if len(profile) < 2:
        return 0.0
    window = min(4, len(profile) - 1)
    return profile[-1] - profile[-1 - window]


def _recommendation(score: float, ndvi_change: float) -> str:
    if score >= 0.75:
        return "Field looks strong. Focus on routine scouting and plan next irrigation window."
    if score >= 0.5:
        if ndvi_change < -0.05:
            return "Moderate stress with a declining NDVI trend. Schedule a scouting pass in the next 48 hours."
        return "Moderate stress. Validate irrigation and tissue samples before the next weather swing."
    if ndvi_change < -0.05:
        return "High stress and falling NDVI. Walk the field now—check water, pests, or equipment issues."
    return "High stress but stable NDVI. Prioritize targeted scouting and review fertigation plans."


def _format_date(ts: str) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return ts


def _build_markdown(
    summary: dict,
    profile: Sequence[float],
    dates: Sequence[str],
    svd: dict,
    advice: str,
) -> str:
    has_profile = len(profile) > 0
    latest = float("nan") if not has_profile else float(profile[-1])
    hi = float("nan") if not has_profile else float(np.max(profile))
    lo = float("nan") if not has_profile else float(np.min(profile))
    date_line = ", ".join(_format_date(ts) for ts in dates) if dates else "not provided"
    return "\n".join(
        [
            f"# Field Report · {summary['field_id']}",
            "",
            f"- **Health score:** {summary['field_health_score']:.2f} ({summary['stress_label']})",
            f"- **Latest NDVI:** {latest:.2f}",
            f"- **NDVI range:** {lo:.2f} – {hi:.2f}",
            f"- **Scenes:** {len(profile)} ({date_line})",
            f"- **SVD rank:** {svd.get('rank', 'n/a')} (captures {svd.get('explained_variance', [0])[0]*100:.1f}% of variance)",
            "",
            "## Recommendation",
            advice,
        ]
    )


def render_report(field_id: str, report_path: Path | None = None) -> None:
    summary = _load_summary(field_id)
    svd = _load_svd(field_id)
    profile = _load_ndvi_profile(field_id)
    manifest_dates = _load_manifest_dates(field_id)
    latest = profile[-1] if profile.size else float("nan")
    delta = _trend_descriptor(profile)
    recommendation = _recommendation(summary["field_health_score"], delta)

    table = Table(title=f"Field {field_id} snapshot", box=None)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Health score", f"{summary['field_health_score']:.2f} ({summary['stress_label']})")
    table.add_row("Latest NDVI", f"{latest:.2f}")
    table.add_row("NDVI min/max", f"{profile.min():.2f} / {profile.max():.2f}")
    table.add_row("NDVI trend", f"{delta:+.2f} over last {min(4, len(profile)-1)} scenes" if len(profile) > 1 else "flat")
    table.add_row("Scenes", str(len(profile)))
    ev = svd.get("explained_variance", [0])
    table.add_row("SVD variance", f"{ev[0]*100:.1f}% first mode" if ev else "n/a")
    table.add_row("Overlay", summary.get("overlay_path", "n/a"))
    console.print(table)
    console.print(Panel(recommendation, title="Action"))

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = _build_markdown(summary, profile, manifest_dates, svd, recommendation)
        report_path.write_text(report, encoding="utf-8")
        console.print(f"Saved report to {report_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a farmer-facing field snapshot")
    parser.add_argument("field_id", type=str, help="Field identifier with processed outputs")
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path to save a markdown report (defaults to data/processed/<field>/report.md)",
    )
    return parser.parse_args()


def main() -> None:  # pragma: no cover
    args = _parse_args()
    report_path = args.report
    if report_path is None:
        report_path = field_processed_dir(args.field_id) / "report.md"
    render_report(args.field_id, report_path)


if __name__ == "__main__":
    main()
