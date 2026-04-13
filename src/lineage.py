from __future__ import annotations

import hashlib
import json
from typing import Any


def _fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()[:12]


def build_lineage_record(
    scenario: dict[str, Any],
    dataset_id: str,
    seed: int,
    summary: dict[str, Any],
    execution_profile: dict[str, Any] | None = None,
    universe_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config_payload = {
        "scenario_id": scenario["scenario_id"],
        "score_column": scenario["score_column"],
        "holding_period": scenario["holding_period"],
        "top_n": scenario["top_n"],
        "cost_bps": scenario["cost_bps"],
        "portfolio_style": scenario["portfolio_style"],
        "sector_neutral": scenario["sector_neutral"],
        "seed": seed,
        "dataset_id": dataset_id,
    }
    factor_payload = {
        "factor_library_version": "factor-lib-v3",
        "macro_overlay_version": "macro-overlay-v2",
        "rebalance_schedule": f"{scenario['holding_period']}B",
        "signal_family": scenario["score_column"],
    }
    execution_payload = {
        "transaction_cost_model": "turnover_linear_bps_plus_execution_shortfall",
        "portfolio_constructor": scenario["portfolio_style"],
        "benchmark": "equal_weight_universe_mean",
        "execution_engine_version": "execution-sim-v2",
        "average_slippage_bps": round(float(summary.get("average_slippage_bps", 0.0)), 4),
        "average_fill_ratio": round(float(summary.get("average_fill_ratio", 1.0)), 4),
    }
    universe_payload = {
        "universe_filter_version": "universe-filter-v2",
        "minimum_price": 8.0,
        "market_cap_quantile": 0.25,
        "dollar_volume_quantile": 0.30,
        "volatility_quantile": 0.92,
        "median_eligible_universe": round(float(summary.get("median_eligible_universe", 0.0)), 2),
        "average_retention_ratio": round(
            1.0 - float(summary.get("average_universe_attrition", 0.0)),
            4,
        ),
    }
    validation_contract = [
        "No future returns available at rebalance time",
        "Factor scores winsorized and z-scored cross-sectionally",
        "Turnover, drawdown, beta, and sector-tilt gates recorded per run",
        "Artifacts and summary metrics persisted for replay and audit",
        "Universe filter decisions and execution diagnostics persisted for review",
    ]

    lineage_fingerprint = _fingerprint(
        {
            "config": config_payload,
            "factor_payload": factor_payload,
            "execution_payload": execution_payload,
            "universe_payload": universe_payload,
            "ending_equity": summary["ending_equity"],
        }
    )

    return {
        "config_fingerprint": lineage_fingerprint,
        "config": config_payload,
        "dataset_snapshot": {
            "dataset_id": dataset_id,
            "dataset_version": f"{dataset_id}-snapshot-v1",
            "calendar": "NYSE business-day synthetic calendar",
            "point_in_time_safe": True,
        },
        "factor_library": factor_payload,
        "execution_model": execution_payload,
        "universe_model": universe_payload,
        "validation_contract": validation_contract,
        "artifacts_version": "tearsheet-v3",
    }
