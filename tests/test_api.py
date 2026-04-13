import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def create_client(tmp_path: Path) -> TestClient:
    os.environ["APP_DATA_DIR"] = str(tmp_path / "app_data")
    if "app.main" in sys.modules:
        importlib.reload(sys.modules["app.main"])
    else:
        importlib.import_module("app.main")
    from app.main import app

    return TestClient(app)


def test_api_platform_runs_and_compare(tmp_path: Path):
    client = create_client(tmp_path)

    system = client.get("/api/system")
    assert system.status_code == 200
    assert system.json()["platform_component_count"] >= 5

    platform = client.get("/api/platform")
    assert platform.status_code == 200
    assert len(platform.json()["components"]) >= 5

    workspace = client.post(
        "/api/workspaces",
        json={"name": "Analyst Pod", "description": "Factor iteration pod"},
    )
    assert workspace.status_code == 200

    run = client.post(
        "/api/runs",
        json={
            "scenario_id": "quality_value_sector_neutral",
            "workspace_id": workspace.json()["workspace_id"],
            "dataset_id": "synthetic_us_equities",
            "label": "Regression Run",
            "seed": 21,
        },
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["validation_report"]["gates"]
    assert payload["validation_report"]["execution_diagnostics"]["average_slippage_bps"] > 0
    assert payload["platform_summary"]["research_readiness"] >= 0
    assert payload["lineage"]["config_fingerprint"]
    assert payload["summary"]["median_eligible_universe"] > 0

    artifact = client.get(f"/api/artifacts/{payload['run_id']}/report.json")
    assert artifact.status_code == 200

    research_ops = client.get("/api/research-ops")
    assert research_ops.status_code == 200
    assert research_ops.json()["average_slippage_bps"] >= 0

    replay = client.post(f"/api/runs/{payload['run_id']}/replay")
    assert replay.status_code == 200

    comparison = client.post(
        "/api/compare",
        json={"run_ids": [payload["run_id"], replay.json()["run_id"]]},
    )
    assert comparison.status_code == 200
    assert len(comparison.json()["rows"]) == 2
