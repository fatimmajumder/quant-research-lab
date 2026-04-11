from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.repository import JsonRepository
from src.artifacts import write_artifacts
from src.data import get_public_datasets
from src.lab import list_scenarios, run_lab_scenario
from src.resources import list_public_resources


class QuantResearchService:
    def __init__(self, app_data_dir: str | None = None) -> None:
        base_dir = app_data_dir or os.environ.get("APP_DATA_DIR", "app_data")
        self.runtime = os.environ.get("APP_RUNTIME", "inline")
        self.repository = JsonRepository(base_dir)

    def system_status(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "runtime": self.runtime,
            "scenario_count": len(list_scenarios()),
            "dataset_count": len(get_public_datasets()),
            "workspace_count": len(self.repository.list_workspaces()),
        }

    def list_scenarios(self) -> list[dict[str, Any]]:
        return list_scenarios()

    def list_public_datasets(self) -> list[dict[str, Any]]:
        synthetic = {
            "dataset_id": "synthetic_us_equities",
            "name": "Synthetic US Equities",
            "description": "Built-in multi-sector synthetic market panel used for deterministic backtests.",
            "source_url": "generated",
            "cadence": "daily",
        }
        return [synthetic, *get_public_datasets()]

    def list_public_resources(self) -> list[dict[str, str]]:
        return list_public_resources()

    def list_workspaces(self) -> list[dict[str, Any]]:
        return self.repository.list_workspaces()

    def create_workspace(self, name: str, description: str) -> dict[str, Any]:
        return self.repository.create_workspace(name=name, description=description)

    def list_runs(self) -> list[dict[str, Any]]:
        return self.repository.list_runs()

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        return run

    def overview(self) -> dict[str, Any]:
        runs = self.list_runs()
        recent = runs[:5]
        featured_candidates = [run for run in runs if run.get("summary", {}).get("sharpe_ratio") is not None]
        featured = max(
            featured_candidates,
            key=lambda item: item["summary"]["sharpe_ratio"],
            default=None,
        )
        return {
            "system": self.system_status(),
            "recent_runs": recent,
            "featured_run": featured,
            "scenarios": self.list_scenarios(),
            "public_resources": self.list_public_resources(),
        }

    def run_research(self, scenario_id: str, seed: int, workspace_id: str | None, label: str | None, dataset_id: str) -> dict[str, Any]:
        run_id = f"run-{uuid4().hex[:12]}"
        created_at = datetime.now(UTC).isoformat()
        seed_payload = {
            "run_id": run_id,
            "created_at": created_at,
            "status": "running",
            "scenario_id": scenario_id,
            "workspace_id": workspace_id or "core-lab",
            "label": label or scenario_id.replace("_", " ").title(),
            "dataset_id": dataset_id,
            "seed": seed,
            "summary": {},
            "artifacts": {},
        }
        self.repository.create_run(seed_payload)

        try:
            report = run_lab_scenario(scenario_id, seed=seed)
            artifact_dir = self.repository.get_artifact_dir(run_id)
            artifacts = write_artifacts(artifact_dir, report)
            updated = self.repository.update_run(
                run_id,
                {
                    "status": "completed",
                    "summary": report["summary"],
                    "artifacts": artifacts,
                    "period_returns": report["period_returns"].to_dict(orient="records"),
                    "equity_curve": report["equity_curve"].to_dict(orient="records"),
                    "factor_exposures": report["factor_exposures"].to_dict(orient="records"),
                    "holdings": report["holdings"].to_dict(orient="records"),
                },
            )
            return updated
        except Exception as exc:
            self.repository.update_run(
                run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                },
            )
            raise

    def replay_run(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        return self.run_research(
            scenario_id=run["scenario_id"],
            seed=int(run["seed"]),
            workspace_id=run.get("workspace_id"),
            label=f"{run['label']} Replay",
            dataset_id=run.get("dataset_id", "synthetic_us_equities"),
        )

    def compare_runs(self, run_ids: list[str]) -> dict[str, Any]:
        runs = [self.get_run(run_id) for run_id in run_ids]
        rows = []
        for run in runs:
            summary = run["summary"]
            rows.append(
                {
                    "run_id": run["run_id"],
                    "label": run["label"],
                    "scenario": summary["scenario_name"],
                    "annualized_return": summary["annualized_return"],
                    "sharpe_ratio": summary["sharpe_ratio"],
                    "max_drawdown": summary["max_drawdown"],
                    "alpha_annualized": summary["alpha_annualized"],
                    "average_turnover": summary["average_turnover"],
                }
            )
        return {"rows": rows}
