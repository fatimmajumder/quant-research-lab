from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioConfig:
    score_column: str
    top_n: int
    holding_period: int
    cost_bps: float
    portfolio_style: str
    sector_neutral: bool


def construct_portfolio_weights(
    snapshot: pd.DataFrame,
    config: PortfolioConfig,
    previous_weights: pd.Series | None = None,
) -> pd.Series:
    ranked = snapshot.copy()
    if config.sector_neutral:
        ranked["effective_score"] = ranked[config.score_column] - ranked.groupby("sector")[config.score_column].transform("mean")
    else:
        ranked["effective_score"] = ranked[config.score_column]

    ranked = ranked.sort_values("effective_score", ascending=False)
    longs = ranked.head(config.top_n).copy()
    shorts = ranked.tail(config.top_n).copy()

    if config.portfolio_style == "risk_scaled":
        long_base = 1.0 / longs["volatility_21"].clip(lower=0.01)
        short_base = 1.0 / shorts["volatility_21"].clip(lower=0.01)
    else:
        long_base = pd.Series(1.0, index=longs.index)
        short_base = pd.Series(1.0, index=shorts.index)

    weights = pd.Series(0.0, index=snapshot["ticker"])
    weights.loc[longs["ticker"]] = 0.5 * long_base.to_numpy() / float(long_base.sum())
    weights.loc[shorts["ticker"]] = -0.5 * short_base.to_numpy() / float(short_base.sum())

    if previous_weights is not None and not previous_weights.empty:
        aligned_previous = previous_weights.reindex(weights.index).fillna(0.0)
        weights = 0.75 * weights + 0.25 * aligned_previous
        gross = float(weights.abs().sum())
        if gross > 0:
            weights = weights / gross

    return weights


def compute_turnover(current: pd.Series, previous: pd.Series | None) -> float:
    if previous is None or previous.empty:
        return float(current.abs().sum())
    aligned_previous = previous.reindex(current.index).fillna(0.0)
    return 0.5 * float((current - aligned_previous).abs().sum())
