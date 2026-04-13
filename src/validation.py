from __future__ import annotations

from typing import Any

import pandas as pd


def _gate(name: str, actual: float, threshold: float, comparator: str, detail: str) -> dict[str, Any]:
    passed = actual <= threshold if comparator == "le" else actual >= threshold
    status = "pass" if passed else "warn"
    return {
        "name": name,
        "actual": round(float(actual), 6),
        "threshold": round(float(threshold), 6),
        "comparator": comparator,
        "status": status,
        "detail": detail,
    }


def build_validation_report(
    summary: dict[str, Any],
    factor_exposures: pd.DataFrame,
    holdings: pd.DataFrame,
    periods: pd.DataFrame,
    execution_profile: pd.DataFrame | None = None,
    universe_audit: pd.DataFrame | None = None,
) -> dict[str, Any]:
    latest_sector_tilts = pd.Series(dtype=float)
    if not holdings.empty:
        sector_rows = holdings.loc[holdings["ticker"].str.startswith("Sector::")].copy()
        if not sector_rows.empty:
            latest_sector_tilts = (
                sector_rows.sort_values("date").groupby("ticker").tail(1).set_index("ticker")["weight"].astype(float)
            )

    avg_beta = float(factor_exposures["beta"].mean()) if not factor_exposures.empty else 0.0
    max_sector_tilt = float(latest_sector_tilts.abs().max()) if not latest_sector_tilts.empty else 0.0
    max_drawdown = abs(float(summary["max_drawdown"]))
    avg_turnover = float(summary["average_turnover"])
    avg_ic = float(summary["average_information_coefficient"])
    hit_rate = float(summary["hit_rate"])
    avg_participation = float(summary.get("average_participation_rate", 0.0))
    avg_slippage_bps = float(summary.get("average_slippage_bps", 0.0))
    avg_fill_ratio = float(summary.get("average_fill_ratio", 1.0))
    retention_ratio = (
        float(universe_audit["retention_ratio"].mean())
        if universe_audit is not None and not universe_audit.empty
        else 1.0 - float(summary.get("average_universe_attrition", 0.0))
    )

    gates = [
        _gate(
            "turnover_budget",
            avg_turnover,
            0.65,
            "le",
            "Average turnover should stay in a range that remains realistic after costs.",
        ),
        _gate(
            "drawdown_budget",
            max_drawdown,
            0.25,
            "le",
            "The sleeve should avoid deep drawdowns that break PM confidence.",
        ),
        _gate(
            "beta_neutrality",
            abs(avg_beta),
            0.35,
            "le",
            "Average beta exposure should stay contained for market-neutral research sleeves.",
        ),
        _gate(
            "sector_tilt_cap",
            max_sector_tilt,
            0.22,
            "le",
            "Latest sector tilts should remain below a concentration threshold.",
        ),
        _gate(
            "signal_quality",
            avg_ic,
            0.015,
            "ge",
            "Average information coefficient should stay positive and material.",
        ),
        _gate(
            "hit_rate_floor",
            hit_rate,
            0.48,
            "ge",
            "Hit rate should remain above a naive coin-flip baseline after costs.",
        ),
        _gate(
            "participation_budget",
            avg_participation,
            0.14,
            "le",
            "Average ADV participation should stay inside a realistic public-demo execution budget.",
        ),
        _gate(
            "slippage_budget_bps",
            avg_slippage_bps,
            18.0,
            "le",
            "Estimated slippage should remain low enough for live review.",
        ),
        _gate(
            "fill_ratio_floor",
            avg_fill_ratio,
            0.90,
            "ge",
            "Average fill ratio should stay high enough for a deployable sleeve.",
        ),
        _gate(
            "universe_retention_floor",
            retention_ratio,
            0.40,
            "ge",
            "Universe filtering should retain enough names to avoid overfitting to a tiny tradable subset.",
        ),
    ]
    statuses = {gate["status"] for gate in gates}
    overall_status = "pass" if statuses == {"pass"} else "warn"

    return {
        "overall_status": overall_status,
        "gates": gates,
        "notes": [
            "Validation runs are tracked alongside artifacts so analysts can explain why a sleeve is promotable.",
            "These gates are intentionally simple public-facing proxies for a larger internal risk and leakage suite.",
        ],
        "period_count": int(len(periods)),
        "execution_diagnostics": {
            "average_participation_rate": round(avg_participation, 6),
            "average_slippage_bps": round(avg_slippage_bps, 4),
            "average_fill_ratio": round(avg_fill_ratio, 4),
        },
        "universe_diagnostics": {
            "average_retention_ratio": round(retention_ratio, 4),
            "average_eligible_universe": round(float(summary.get("median_eligible_universe", 0.0)), 2),
        },
    }
