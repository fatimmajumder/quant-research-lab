from __future__ import annotations

import argparse
import time
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def wait_for_run(base_url: str, run_id: str, timeout: float = 30.0) -> dict[str, object]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        payload = requests.get(f"{base_url}/api/runs/{run_id}", timeout=10).json()
        if payload.get("status") == "completed":
            return payload
        time.sleep(0.5)
    raise TimeoutError(f"Run {run_id} did not finish in time")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test a local or hosted Quant Research Lab deployment.")
    parser.add_argument("base_url", help="Base URL like http://127.0.0.1:8000")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    assert requests.get(f"{base_url}/health", timeout=10).json()["status"] == "ok"
    system = requests.get(f"{base_url}/api/system", timeout=10).json()
    assert system["scenario_count"] >= 5
    platform = requests.get(f"{base_url}/api/platform", timeout=10).json()
    assert len(platform["components"]) >= 5

    workspace = requests.post(
        f"{base_url}/api/workspaces",
        json={"name": "Smoke Test Pod", "description": "Quick verification workspace"},
        timeout=10,
    ).json()
    run = requests.post(
        f"{base_url}/api/runs",
        json={
            "scenario_id": "quality_value_sector_neutral",
            "workspace_id": workspace["workspace_id"],
            "dataset_id": "synthetic_us_equities",
            "label": "Smoke Run",
            "seed": 21,
        },
        timeout=20,
    ).json()
    completed = wait_for_run(base_url, run["run_id"])
    assert completed["platform_summary"]["research_readiness"] >= 0
    assert completed["validation_report"]["gates"]
    assert completed["lineage"]["config_fingerprint"]

    replay = requests.post(f"{base_url}/api/runs/{run['run_id']}/replay", timeout=20).json()
    replay_completed = wait_for_run(base_url, replay["run_id"])
    comparison = requests.post(
        f"{base_url}/api/compare",
        json={"run_ids": [run["run_id"], replay_completed["run_id"]]},
        timeout=10,
    ).json()
    assert len(comparison["rows"]) == 2
    report = requests.get(f"{base_url}/api/artifacts/{run['run_id']}/report.json", timeout=10)
    assert report.status_code == 200
    print("smoke test passed")


if __name__ == "__main__":
    main()
