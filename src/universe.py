from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class UniverseFilterConfig:
    minimum_price: float = 8.0
    market_cap_quantile: float = 0.25
    dollar_volume_quantile: float = 0.30
    volatility_quantile: float = 0.92


def apply_universe_filters(
    snapshot: pd.DataFrame,
    *,
    score_column: str,
    config: UniverseFilterConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    config = config or UniverseFilterConfig()
    working = snapshot.copy()
    start_count = int(len(working))
    if working.empty:
        return working, {
            "starting_universe": 0,
            "eligible_universe": 0,
            "retention_ratio": 0.0,
            "attrition_ratio": 1.0,
            "thresholds": {},
            "failure_breakdown": {},
            "top_names": [],
        }

    min_market_cap = float(working["market_cap"].quantile(config.market_cap_quantile))
    min_dollar_volume = float(working["dollar_volume"].quantile(config.dollar_volume_quantile))
    max_volatility = float(working["volatility_21"].quantile(config.volatility_quantile))

    checks = {
        "price_floor": working["price"].astype(float) >= config.minimum_price,
        "market_cap_floor": working["market_cap"].astype(float) >= min_market_cap,
        "liquidity_floor": working["dollar_volume"].astype(float) >= min_dollar_volume,
        "volatility_cap": working["volatility_21"].astype(float) <= max_volatility,
        "signal_available": working[score_column].notna(),
    }
    combined = pd.concat(checks, axis=1)
    eligible_mask = combined.all(axis=1)
    eligible = working.loc[eligible_mask].copy()

    top_names = (
        eligible.nlargest(min(5, len(eligible)), score_column)[["ticker", "sector", score_column]]
        .rename(columns={score_column: "signal"})
        .to_dict(orient="records")
        if not eligible.empty
        else []
    )

    audit = {
        "starting_universe": start_count,
        "eligible_universe": int(len(eligible)),
        "retention_ratio": round(float(len(eligible)) / max(start_count, 1), 4),
        "attrition_ratio": round(1.0 - float(len(eligible)) / max(start_count, 1), 4),
        "thresholds": {
            "minimum_price": round(config.minimum_price, 2),
            "minimum_market_cap": round(min_market_cap, 2),
            "minimum_dollar_volume": round(min_dollar_volume, 2),
            "maximum_volatility_21": round(max_volatility, 6),
        },
        "failure_breakdown": {
            name: int((~mask).sum())
            for name, mask in checks.items()
        },
        "top_names": top_names,
    }
    return eligible, audit
