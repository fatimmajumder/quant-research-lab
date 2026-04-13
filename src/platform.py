from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PlatformComponent:
    name: str
    layer: str
    role: str
    status: str


PLATFORM_COMPONENTS = [
    PlatformComponent(
        "point_in_time_ingestion",
        "data",
        "Builds leakage-aware snapshots with dataset versioning and reproducible calendars.",
        "active",
    ),
    PlatformComponent(
        "factor_library",
        "research",
        "Computes cross-sectional scores, regime overlays, and signal diagnostics.",
        "active",
    ),
    PlatformComponent(
        "portfolio_constructor",
        "research",
        "Forms long-short books with sector controls, turnover smoothing, and cost modeling.",
        "active",
    ),
    PlatformComponent(
        "universe_filter_engine",
        "research",
        "Applies tradability, liquidity, and volatility screens while recording retention and attrition diagnostics.",
        "active",
    ),
    PlatformComponent(
        "execution_simulator",
        "risk",
        "Estimates ADV participation, fill ratios, and implementation shortfall before a sleeve is considered promotable.",
        "active",
    ),
    PlatformComponent(
        "experiment_tracker",
        "platform",
        "Persists runs, artifacts, labels, workspaces, and replay lineage for auditability.",
        "active",
    ),
    PlatformComponent(
        "validation_suite",
        "risk",
        "Applies public-facing risk gates for drawdown, turnover, beta, and sector concentration.",
        "active",
    ),
    PlatformComponent(
        "tearsheet_service",
        "product",
        "Exports charts, markdown, attribution tables, and downloadable run bundles.",
        "active",
    ),
]

ENGINEERING_SIGNALS = [
    "Point-in-time research contracts and reproducible experiment lineage",
    "Workspace-oriented experiment tracking and replayable tearsheet bundles",
    "Exposure control, attribution, and validation gates baked into every run",
    "Universe filtering and execution simulation visible in artifacts instead of hidden inside a notebook",
    "CI-ready repo surface with scripts, smoke tests, and deploy-friendly app packaging",
]


def get_research_platform() -> dict[str, Any]:
    return {
        "platform_name": "Quant Research Platform",
        "components": [asdict(component) for component in PLATFORM_COMPONENTS],
        "engineering_signals": ENGINEERING_SIGNALS,
        "validation_gates": [
            "turnover_budget",
            "drawdown_budget",
            "beta_neutrality",
            "sector_tilt_cap",
            "signal_quality",
            "hit_rate_floor",
            "participation_budget",
            "slippage_budget_bps",
            "fill_ratio_floor",
            "universe_retention_floor",
        ],
        "artifact_bundle": [
            "report.json",
            "summary.md",
            "research_brief.md",
            "lineage.json",
            "validation_report.json",
            "platform_summary.json",
            "universe_audit.json",
            "execution_summary.json",
            "factor_attribution.csv",
            "sector_attribution.csv",
            "equity_curve.svg",
            "drawdown.svg",
            "factor_exposures.svg",
            "sector_tilts.svg",
            "ic_trace.svg",
            "capacity_profile.svg",
            "execution_profile.csv",
            "universe_audit.csv",
            "slippage_profile.svg",
            "universe_retention.svg",
        ],
    }


def build_platform_summary(
    summary: dict[str, Any],
    lineage: dict[str, Any],
    validation_report: dict[str, Any],
    attribution: dict[str, Any],
    execution_profile: dict[str, Any] | None = None,
    universe_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sharpe_component = min(max(float(summary["sharpe_ratio"]) / 1.8, 0.0), 1.0)
    alpha_component = min(max(float(summary["alpha_annualized"]) / 0.12, 0.0), 1.0)
    hit_rate_component = min(max(float(summary["hit_rate"]), 0.0), 1.0)
    drawdown_component = 1.0 - min(abs(float(summary["max_drawdown"])) / 0.25, 1.0)
    execution_component = 1.0 - min(float(summary.get("average_slippage_bps", 0.0)) / 22.0, 1.0)
    universe_component = min(
        max(1.0 - float(summary.get("average_universe_attrition", 0.0)), 0.0),
        1.0,
    )
    readiness = 100.0 * (
        0.23 * sharpe_component
        + 0.19 * alpha_component
        + 0.18 * hit_rate_component
        + 0.20 * drawdown_component
        + 0.10 * execution_component
        + 0.10 * universe_component
    )
    if readiness >= 72.0 and validation_report["overall_status"] == "pass":
        execution_mode = "promotable_research"
    elif float(summary.get("average_slippage_bps", 0.0)) > 18.0:
        execution_mode = "capacity_review"
    elif readiness >= 55.0:
        execution_mode = "watchlist_iteration"
    else:
        execution_mode = "needs_rework"

    dominant_factor = attribution["factor_contributions"][0]["factor"] if attribution["factor_contributions"] else "n/a"

    return {
        "research_readiness": round(readiness, 2),
        "execution_mode": execution_mode,
        "tracker": {
            "lineage_fingerprint": lineage["config_fingerprint"],
            "dataset_version": lineage["dataset_snapshot"]["dataset_version"],
            "artifacts_version": lineage["artifacts_version"],
        },
        "ops_summary": {
            "average_slippage_bps": round(float(summary.get("average_slippage_bps", 0.0)), 4),
            "average_fill_ratio": round(float(summary.get("average_fill_ratio", 1.0)), 4),
            "median_eligible_universe": round(float(summary.get("median_eligible_universe", 0.0)), 2),
            "average_universe_attrition": round(float(summary.get("average_universe_attrition", 0.0)), 4),
        },
        "component_health": [
            {
                "name": component.name,
                "status": "active" if validation_report["overall_status"] == "pass" else "monitor",
                "detail": component.role,
            }
            for component in PLATFORM_COMPONENTS
        ],
        "operator_notes": [
            f"Dominant attribution driver: {dominant_factor}",
            f"Validation status: {validation_report['overall_status']}",
            f"Scenario periods evaluated: {summary['period_count']}",
            f"Average slippage: {float(summary.get('average_slippage_bps', 0.0)):.2f} bps",
            f"Universe retention: {(1.0 - float(summary.get('average_universe_attrition', 0.0))):.1%}",
        ],
    }
