from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.data import build_synthetic_market_panel
from src.factors import compute_factor_signals
from src.portfolio import PortfolioConfig, compute_turnover, construct_portfolio_weights


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_id: str
    name: str
    description: str
    score_column: str
    top_n: int
    holding_period: int
    cost_bps: float
    portfolio_style: str
    sector_neutral: bool


def _max_drawdown(equity_curve: pd.Series) -> float:
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1.0
    return float(drawdown.min())


def run_backtest(config: ScenarioConfig, seed: int = 21) -> dict[str, object]:
    panel, macro = build_synthetic_market_panel(seed=seed)
    signals = compute_factor_signals(panel, macro)
    price_frame = panel.pivot(index="date", columns="ticker", values="price")
    forward_returns = price_frame.pct_change(config.holding_period).shift(-config.holding_period)
    benchmark = price_frame.pct_change(config.holding_period).shift(-config.holding_period).mean(axis=1)

    rebalance_dates = signals["date"].drop_duplicates().sort_values().iloc[126:-config.holding_period:config.holding_period]
    holdings_rows: list[dict[str, object]] = []
    period_rows: list[dict[str, object]] = []
    exposure_rows: list[dict[str, object]] = []
    previous_weights = pd.Series(dtype=float)
    portfolio_config = PortfolioConfig(
        score_column=config.score_column,
        top_n=config.top_n,
        holding_period=config.holding_period,
        cost_bps=config.cost_bps,
        portfolio_style=config.portfolio_style,
        sector_neutral=config.sector_neutral,
    )

    for current_date in rebalance_dates:
        snapshot = signals.loc[signals["date"] == current_date].copy()
        current_forward = forward_returns.loc[current_date]
        snapshot["forward_return"] = snapshot["ticker"].map(current_forward.to_dict())
        snapshot = snapshot.dropna(subset=["forward_return", "volatility_21"])
        if len(snapshot) < config.top_n * 2:
            continue

        weights = construct_portfolio_weights(snapshot, portfolio_config, previous_weights)
        realized = float(
            snapshot["ticker"].map(weights.to_dict()).fillna(0.0).to_numpy() @ snapshot["forward_return"].to_numpy()
        )
        benchmark_return = float(benchmark.loc[current_date])
        turnover = compute_turnover(weights, previous_weights)
        transaction_cost = turnover * config.cost_bps / 10_000.0
        net_return = realized - transaction_cost
        ic = float(snapshot[config.score_column].rank().corr(snapshot["forward_return"].rank()))
        weighted_snapshot = snapshot.assign(weight=snapshot["ticker"].map(weights).fillna(0.0))
        selected = weighted_snapshot.loc[weighted_snapshot["weight"] != 0.0].copy()
        gross_exposure = float(weights.abs().sum())
        net_exposure = float(weights.sum())
        capacity_proxy = float((selected["weight"].abs() * selected["dollar_volume"]).sum()) if not selected.empty else 0.0
        max_name_weight = float(selected["weight"].abs().max()) if not selected.empty else 0.0

        exposure_rows.append(
            {
                "date": current_date,
                "value": float((snapshot["ticker"].map(weights).fillna(0.0) * snapshot["book_to_price_z"]).sum()),
                "quality": float((snapshot["ticker"].map(weights).fillna(0.0) * snapshot["quality_z"]).sum()),
                "momentum": float((snapshot["ticker"].map(weights).fillna(0.0) * snapshot["momentum_63_z"]).sum()),
                "stability": float((snapshot["ticker"].map(weights).fillna(0.0) * snapshot["stability_z"]).sum()),
                "beta": float((snapshot["ticker"].map(weights).fillna(0.0) * snapshot["beta_z"]).sum()),
            }
        )

        sector_tilts = snapshot.assign(weight=snapshot["ticker"].map(weights).fillna(0.0)).groupby("sector")["weight"].sum()
        for sector, weight in sector_tilts.items():
            holdings_rows.append(
                {
                    "date": current_date,
                    "ticker": f"Sector::{sector}",
                    "sector": sector,
                    "side": "tilt",
                    "weight": float(weight),
                    "signal": 0.0,
                    "forward_return": 0.0,
                }
            )

        for _, row in selected.sort_values("weight", ascending=False).iterrows():
            holdings_rows.append(
                {
                    "date": current_date,
                    "ticker": row["ticker"],
                    "sector": row["sector"],
                    "side": "long" if row["weight"] > 0 else "short",
                    "weight": float(row["weight"]),
                    "signal": float(row[config.score_column]),
                    "forward_return": float(row["forward_return"]),
                }
            )

        period_rows.append(
            {
                "date": current_date,
                "gross_return": realized,
                "net_return": net_return,
                "benchmark_return": benchmark_return,
                "alpha": net_return - benchmark_return,
                "turnover": turnover,
                "information_coefficient": ic,
                "transaction_cost": transaction_cost,
                "gross_exposure": gross_exposure,
                "net_exposure": net_exposure,
                "capacity_proxy": capacity_proxy,
                "max_name_weight": max_name_weight,
                "universe_size": int(len(snapshot)),
            }
        )
        previous_weights = weights

    periods = pd.DataFrame(period_rows)
    exposures = pd.DataFrame(exposure_rows)
    holdings = pd.DataFrame(holdings_rows)
    if periods.empty:
        raise RuntimeError("Backtest did not produce any periods.")

    equity_curve = (1.0 + periods["net_return"]).cumprod()
    benchmark_curve = (1.0 + periods["benchmark_return"]).cumprod()
    ann_factor = 252.0 / config.holding_period
    total_years = max((config.holding_period * len(periods)) / 252.0, 1e-6)
    annualized_return = float(equity_curve.iloc[-1] ** (1.0 / total_years) - 1.0)
    annualized_vol = float(periods["net_return"].std(ddof=0) * np.sqrt(ann_factor))
    sharpe = annualized_return / annualized_vol if annualized_vol else 0.0
    alpha_vol = float(periods["alpha"].std(ddof=0) * np.sqrt(ann_factor))
    alpha_ann = float(periods["alpha"].mean() * ann_factor)

    summary = {
        "scenario_id": config.scenario_id,
        "scenario_name": config.name,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_vol,
        "sharpe_ratio": float(sharpe),
        "max_drawdown": _max_drawdown(equity_curve),
        "hit_rate": float((periods["net_return"] > 0).mean()),
        "alpha_annualized": alpha_ann,
        "alpha_information_ratio": alpha_ann / alpha_vol if alpha_vol else 0.0,
        "average_turnover": float(periods["turnover"].mean()),
        "average_information_coefficient": float(periods["information_coefficient"].mean()),
        "period_count": int(len(periods)),
        "ending_equity": float(equity_curve.iloc[-1]),
        "benchmark_ending_equity": float(benchmark_curve.iloc[-1]),
        "rebalance_count": int(len(periods)),
        "average_transaction_cost": float(periods["transaction_cost"].mean()),
        "average_gross_exposure": float(periods["gross_exposure"].mean()),
        "average_net_exposure": float(periods["net_exposure"].mean()),
        "median_capacity_proxy": float(periods["capacity_proxy"].median()),
        "max_name_weight": float(periods["max_name_weight"].max()),
    }

    return {
        "summary": summary,
        "period_returns": periods,
        "equity_curve": pd.DataFrame(
            {
                "date": periods["date"],
                "strategy_equity": equity_curve,
                "benchmark_equity": benchmark_curve,
                "drawdown": equity_curve / equity_curve.cummax() - 1.0,
            }
        ),
        "factor_exposures": exposures,
        "holdings": holdings,
        "macro": macro,
    }
