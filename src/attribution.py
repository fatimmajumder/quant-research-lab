from __future__ import annotations

from typing import Any

import pandas as pd


def build_attribution(
    periods: pd.DataFrame,
    factor_exposures: pd.DataFrame,
    holdings: pd.DataFrame,
) -> dict[str, Any]:
    if periods.empty:
        return {
            "factor_contributions": [],
            "sector_contributions": [],
            "diagnostics": {},
        }

    merged = periods[["date", "alpha", "information_coefficient", "turnover"]].merge(
        factor_exposures,
        on="date",
        how="left",
    )
    factor_columns = [column for column in factor_exposures.columns if column != "date"]
    factor_rows = []
    for column in factor_columns:
        contribution = float((merged[column].fillna(0.0) * merged["alpha"].fillna(0.0)).sum())
        factor_rows.append(
            {
                "factor": column,
                "contribution": contribution,
                "mean_exposure": float(merged[column].fillna(0.0).mean()),
            }
        )
    factor_rows.sort(key=lambda item: abs(item["contribution"]), reverse=True)

    sector_rows: list[dict[str, Any]] = []
    selected = holdings.loc[~holdings["ticker"].str.startswith("Sector::")].copy() if not holdings.empty else holdings
    if not selected.empty and "sector" in selected.columns:
        selected["contribution"] = selected["weight"].astype(float) * selected["forward_return"].astype(float)
        sector_frame = (
            selected.groupby("sector")
            .agg(
                contribution=("contribution", "sum"),
                average_weight=("weight", "mean"),
                positions=("ticker", "count"),
            )
            .reset_index()
            .sort_values("contribution", ascending=False)
        )
        sector_rows = sector_frame.to_dict(orient="records")

    diagnostics = {
        "mean_information_coefficient": float(periods["information_coefficient"].mean()),
        "mean_turnover": float(periods["turnover"].mean()),
        "best_alpha_period": float(periods["alpha"].max()),
        "worst_alpha_period": float(periods["alpha"].min()),
    }
    return {
        "factor_contributions": factor_rows,
        "sector_contributions": sector_rows,
        "diagnostics": diagnostics,
    }
