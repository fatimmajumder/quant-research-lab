from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ExecutionConfig:
    portfolio_notional: float = 10_000_000.0
    max_participation_rate: float = 0.12
    base_slippage_bps: float = 4.0
    spread_factor_bps: float = 26.0
    volatility_factor_bps: float = 90.0


def simulate_execution(
    selected: pd.DataFrame,
    *,
    date: pd.Timestamp,
    config: ExecutionConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    config = config or ExecutionConfig()
    if selected.empty:
        empty = pd.DataFrame(
            columns=[
                "date",
                "ticker",
                "sector",
                "side",
                "weight",
                "estimated_trade_dollars",
                "participation_rate",
                "slippage_bps",
                "fill_ratio",
                "implementation_shortfall_return",
                "stress_flag",
            ]
        )
        return empty, {
            "average_participation_rate": 0.0,
            "average_slippage_bps": 0.0,
            "average_fill_ratio": 0.0,
            "implementation_shortfall_return": 0.0,
            "stressed_trade_count": 0,
        }

    execution = selected.copy()
    if "side" not in execution.columns:
        execution["side"] = execution["weight"].astype(float).apply(lambda value: "long" if value > 0 else "short")
    execution["estimated_trade_dollars"] = (
        execution["weight"].abs().astype(float) * config.portfolio_notional
    )
    execution["participation_rate"] = (
        execution["estimated_trade_dollars"]
        / execution["dollar_volume"].astype(float).clip(lower=1.0)
    )
    execution["slippage_bps"] = (
        config.base_slippage_bps
        + config.spread_factor_bps * execution["participation_rate"].clip(lower=0.0)
        + config.volatility_factor_bps * execution["volatility_21"].astype(float).clip(lower=0.0)
    )
    execution["fill_ratio"] = (
        1.0
        - (execution["participation_rate"] - config.max_participation_rate).clip(lower=0.0) * 1.4
    ).clip(lower=0.72, upper=1.0)
    execution["implementation_shortfall_return"] = (
        execution["weight"].abs().astype(float)
        * execution["slippage_bps"].astype(float)
        / 10_000.0
        * (2.0 - execution["fill_ratio"].astype(float))
    )
    execution["stress_flag"] = (
        (execution["participation_rate"] > config.max_participation_rate)
        | (execution["slippage_bps"] > 18.0)
    )
    execution["date"] = date

    summary = {
        "average_participation_rate": round(float(execution["participation_rate"].mean()), 6),
        "average_slippage_bps": round(float(execution["slippage_bps"].mean()), 4),
        "average_fill_ratio": round(float(execution["fill_ratio"].mean()), 4),
        "implementation_shortfall_return": round(
            float(execution["implementation_shortfall_return"].sum()),
            6,
        ),
        "stressed_trade_count": int(execution["stress_flag"].sum()),
    }

    keep_columns = [
        "date",
        "ticker",
        "sector",
        "side",
        "weight",
        "estimated_trade_dollars",
        "participation_rate",
        "slippage_bps",
        "fill_ratio",
        "implementation_shortfall_return",
        "stress_flag",
    ]
    return execution[keep_columns].reset_index(drop=True), summary
