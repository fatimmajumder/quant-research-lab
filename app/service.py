from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.repository import JsonRepository
from src.attribution import build_attribution
from src.artifacts import write_artifacts
from src.data import get_public_datasets
from src.lab import get_scenario_config, list_scenarios, run_lab_scenario
from src.lineage import build_lineage_record
from src.platform import build_platform_summary, get_research_platform
from src.resources import list_public_resources
from src.validation import build_validation_report


class QuantResearchService:
    def __init__(self, app_data_dir: str | None = None) -> None:
        base_dir = app_data_dir or os.environ.get("APP_DATA_DIR", "app_data")
        self.runtime = os.environ.get("APP_RUNTIME", "inline")
        self.repository = JsonRepository(base_dir)

    def system_status(self) -> dict[str, Any]:
        platform = get_research_platform()
        return {
            "status": "ok",
            "runtime": self.runtime,
            "scenario_count": len(list_scenarios()),
            "dataset_count": len(get_public_datasets()),
            "workspace_count": len(self.repository.list_workspaces()),
            "platform_component_count": len(platform["components"]),
            "validation_gate_count": len(platform["validation_gates"]),
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

    def platform(self) -> dict[str, Any]:
        return get_research_platform()

    def research_ops(self) -> dict[str, Any]:
        runs = self.list_runs()
        completed = [run for run in runs if run.get("status") == "completed" and run.get("summary")]
        if completed:
            average_slippage_bps = sum(
                float(run["summary"].get("average_slippage_bps", 0.0)) for run in completed
            ) / len(completed)
            average_fill_ratio = sum(
                float(run["summary"].get("average_fill_ratio", 1.0)) for run in completed
            ) / len(completed)
            average_retention = sum(
                1.0 - float(run["summary"].get("average_universe_attrition", 0.0))
                for run in completed
            ) / len(completed)
        else:
            average_slippage_bps = 0.0
            average_fill_ratio = 1.0
            average_retention = 0.0

        latest = completed[0] if completed else None
        return {
            "average_slippage_bps": round(average_slippage_bps, 4),
            "average_fill_ratio": round(average_fill_ratio, 4),
            "average_universe_retention": round(average_retention, 4),
            "latest_run_id": latest["run_id"] if latest else None,
            "latest_execution_mode": latest.get("platform_summary", {}).get("execution_mode") if latest else None,
        }

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
            "platform": self.platform(),
            "research_ops": self.research_ops(),
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
            scenario = get_scenario_config(scenario_id)
            validation_report = build_validation_report(
                report["summary"],
                report["factor_exposures"],
                report["holdings"],
                report["period_returns"],
                execution_profile=report["execution_profile"],
                universe_audit=report["universe_audit"],
            )
            attribution = build_attribution(
                report["period_returns"],
                report["factor_exposures"],
                report["holdings"],
            )
            lineage = build_lineage_record(
                scenario=scenario,
                dataset_id=dataset_id,
                seed=seed,
                summary=report["summary"],
                execution_profile={
                    "average_slippage_bps": report["summary"]["average_slippage_bps"],
                    "average_fill_ratio": report["summary"]["average_fill_ratio"],
                },
                universe_audit={
                    "median_eligible_universe": report["summary"]["median_eligible_universe"],
                    "average_universe_attrition": report["summary"]["average_universe_attrition"],
                },
            )
            platform_summary = build_platform_summary(
                report["summary"],
                lineage=lineage,
                validation_report=validation_report,
                attribution=attribution,
                execution_profile={
                    "average_slippage_bps": report["summary"]["average_slippage_bps"],
                },
                universe_audit={
                    "average_universe_attrition": report["summary"]["average_universe_attrition"],
                },
            )
            report["validation_report"] = validation_report
            report["attribution"] = attribution
            report["lineage"] = lineage
            report["platform_summary"] = platform_summary
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
                    "execution_profile": report["execution_profile"].to_dict(orient="records"),
                    "universe_audit": report["universe_audit"].to_dict(orient="records"),
                    "validation_report": validation_report,
                    "attribution": attribution,
                    "lineage": lineage,
                    "platform_summary": platform_summary,
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
                    "average_slippage_bps": summary.get("average_slippage_bps"),
                    "average_fill_ratio": summary.get("average_fill_ratio"),
                    "median_eligible_universe": summary.get("median_eligible_universe"),
                    "research_readiness": run.get("platform_summary", {}).get("research_readiness"),
                    "fingerprint": run.get("lineage", {}).get("config_fingerprint"),
                }
            )
        return {"rows": rows}
