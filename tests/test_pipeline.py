from pathlib import Path


def test_pipeline_roundtrip(tmp_path: Path, monkeypatch):
    field_id = "test-field"
    monkeypatch.setenv("MAT_DATA_DIR", str(tmp_path))

    # Defer imports until after MAT_DATA_DIR is set so modules pick up the test path.
    from src.ingest.run_ingest import run_ingest
    from src.preprocessing.run_preprocessing import run_preprocessing
    from src.temporal_svd.run_svd import run_svd
    from src.analysis.build_overlay import run_analysis
    from src.utils.paths import field_raw_dir, field_processed_dir

    run_ingest(field_id, zip_code="68430", start="2024-01-01", end="2024-02-01")
    raw_dir = field_raw_dir(field_id)
    assert (raw_dir / "ingest_manifest.json").exists()

    run_preprocessing(field_id, tile_size=16)
    processed_dir = field_processed_dir(field_id)
    ndvi_path = processed_dir / "ndvi_stack.npz"
    assert ndvi_path.exists()

    run_svd(field_id, rank=2)
    assert (processed_dir / "svd_stats.json").exists()

    summary = run_analysis(field_id)
    assert summary["field_health_score"] >= 0.0
    assert Path(summary["overlay_path"]).exists()
