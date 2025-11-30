from pathlib import Path


def test_pipeline_roundtrip(tmp_path: Path, monkeypatch):
    field_id = "test-field"
    monkeypatch.setenv("MAT_DATA_DIR", str(tmp_path))

    # Defer imports until after MAT_DATA_DIR is set so modules pick up the test path.
    from src.pipeline import run_analysis, run_ingest, run_pipeline, run_preprocessing, run_temporal_svd
    from src.utils.paths import field_processed_dir, field_raw_dir

    run_ingest(field_id, zip_code="68430", start="2024-01-01", end="2024-02-01")
    raw_dir = field_raw_dir(field_id)
    assert (raw_dir / "ingest_manifest.json").exists()

    run_preprocessing(field_id, tile_size=16)
    processed_dir = field_processed_dir(field_id)
    ndvi_path = processed_dir / "ndvi_stack.npz"
    assert ndvi_path.exists()

    run_temporal_svd(field_id, rank=2)
    assert (processed_dir / "svd_stats.json").exists()

    summary = run_analysis(field_id, use_cnn=True)
    assert summary["field_health_score"] >= 0.0
    assert Path(summary["overlay_path"]).exists()
    assert Path(summary["svd_overlay_path"]).exists()
    assert "cnn" in summary
    data_path = Path(summary["overlay_data_path"])
    assert data_path.exists()
    import json
    overlay_data = json.loads(data_path.read_text())
    assert overlay_data["values"]
    assert Path(summary["svd_overlay_data_path"]).exists()

    # End-to-end helper should also work
    summary = run_pipeline(
        "pipeline-field",
        zip_code="12345",
        start="2024-03-01",
        end="2024-03-10",
        tile_size=8,
        rank=2,
        use_cnn=False,
    )
    assert summary["field_id"] == "pipeline-field"
