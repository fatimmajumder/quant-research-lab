from __future__ import annotations

import numpy as np
import pandas as pd


def _zscore(series: pd.Series) -> pd.Series:
    std = float(series.std(ddof=0))
    if std == 0.0 or np.isnan(std):
        return pd.Series(0.0, index=series.index)
    return (series - float(series.mean())) / std


def _winsorize(series: pd.Series, lower: float = 0.05, upper: float = 0.95) -> pd.Series:
    low = float(series.quantile(lower))
    high = float(series.quantile(upper))
    return series.clip(low, high)


def _sector_neutralize(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column] - frame.groupby(["date", "sector"])[column].transform("mean")


def compute_factor_signals(panel: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    working = panel.sort_values(["ticker", "date"]).copy()
    working["momentum_21"] = working.groupby("ticker")["price"].pct_change(21)
    working["momentum_63"] = working.groupby("ticker")["price"].pct_change(63)
    working["reversal_5"] = -working.groupby("ticker")["price"].pct_change(5)
    working["volatility_21"] = working.groupby("ticker")["return"].transform(
        lambda values: values.rolling(21).std()
    )
    working["volume_21"] = working.groupby("ticker")["dollar_volume"].transform(
        lambda values: values.rolling(21).mean()
    )
    working["price_vs_63d_mean"] = working.groupby("ticker")["price"].transform(
        lambda values: values / values.rolling(63).mean() - 1.0
    )

    macro_frame = macro.copy()
    macro_frame["macro_regime_z"] = _zscore(macro_frame["macro_regime"])
    merged = working.merge(
        macro_frame[["date", "growth", "stress", "macro_regime_z"]],
        on="date",
        how="left",
    )

    cross_section = [
        "book_to_price",
        "quality",
        "profitability",
        "momentum_21",
        "momentum_63",
        "reversal_5",
        "volatility_21",
        "liquidity",
        "price_vs_63d_mean",
        "beta",
    ]
    for column in cross_section:
        cleaned = merged.groupby("date")[column].transform(_winsorize)
        merged[f"{column}_z"] = cleaned.groupby(merged["date"]).transform(_zscore)

    merged["stability_z"] = -merged["volatility_21_z"]
    merged["size_z"] = -merged.groupby("date")["size"].transform(_zscore)
    merged["quality_value_raw"] = (
        0.35 * merged["book_to_price_z"]
        + 0.30 * merged["quality_z"]
        + 0.20 * merged["profitability_z"]
        + 0.15 * merged["size_z"]
    )
    merged["momentum_regime_raw"] = (
        0.45 * merged["momentum_63_z"]
        + 0.20 * merged["momentum_21_z"]
        + 0.10 * merged["price_vs_63d_mean_z"]
        + 0.25 * merged["macro_regime_z"]
    )
    merged["defensive_raw"] = (
        0.40 * merged["quality_z"]
        + 0.35 * merged["stability_z"]
        + 0.15 * merged["profitability_z"]
        - 0.10 * merged["beta_z"]
    )
    merged["earnings_revision_raw"] = (
        0.35 * merged["quality_z"]
        + 0.25 * merged["profitability_z"]
        + 0.20 * merged["momentum_21_z"]
        + 0.10 * merged["momentum_63_z"]
        + 0.10 * merged["macro_regime_z"]
    )
    merged["liquidity_resilience_raw"] = (
        0.35 * merged["quality_z"]
        + 0.20 * merged["stability_z"]
        + 0.20 * merged["book_to_price_z"]
        + 0.15 * merged["liquidity_z"]
        - 0.10 * merged["beta_z"]
    )

    merged["quality_value_score"] = _sector_neutralize(merged, "quality_value_raw")
    merged["momentum_regime_score"] = _sector_neutralize(merged, "momentum_regime_raw")
    merged["defensive_score"] = _sector_neutralize(merged, "defensive_raw")
    merged["earnings_revision_score"] = _sector_neutralize(merged, "earnings_revision_raw")
    merged["liquidity_resilience_score"] = _sector_neutralize(merged, "liquidity_resilience_raw")
    merged["composite_score"] = (
        0.30 * merged["quality_value_score"]
        + 0.25 * merged["momentum_regime_score"]
        + 0.20 * merged["defensive_score"]
        + 0.15 * merged["earnings_revision_score"]
        + 0.10 * merged["liquidity_resilience_score"]
    )

    signal_columns = [
        "date",
        "ticker",
        "sector",
        "return",
        "price",
        "market_cap",
        "dollar_volume",
        "book_to_price",
        "quality",
        "profitability",
        "beta",
        "size",
        "liquidity",
        "momentum_21",
        "momentum_63",
        "reversal_5",
        "volatility_21",
        "quality_value_score",
        "momentum_regime_score",
        "defensive_score",
        "earnings_revision_score",
        "liquidity_resilience_score",
        "composite_score",
        "book_to_price_z",
        "quality_z",
        "profitability_z",
        "momentum_63_z",
        "stability_z",
        "beta_z",
        "liquidity_z",
        "macro_regime_z",
    ]
    signal_frame = merged[signal_columns].dropna().reset_index(drop=True)
    return signal_frame
