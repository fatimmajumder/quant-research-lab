from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.data import build_synthetic_market_panel
from src.execution import simulate_execution
from src.factors import compute_factor_signals
from src.portfolio import PortfolioConfig, compute_turnover, construct_portfolio_weights
from src.universe import apply_universe_filters


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
    execution_rows: list[dict[str, object]] = []
    universe_audit_rows: list[dict[str, object]] = []
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
        eligible_snapshot, universe_audit = apply_universe_filters(
            snapshot,
            score_column=config.score_column,
        )
        universe_audit_rows.append({"date": current_date, **universe_audit})
        if len(eligible_snapshot) < config.top_n * 2:
            continue

        weights = construct_portfolio_weights(eligible_snapshot, portfolio_config, previous_weights)
        realized = float(
            eligible_snapshot["ticker"].map(weights.to_dict()).fillna(0.0).to_numpy()
            @ eligible_snapshot["forward_return"].to_numpy()
        )
        benchmark_return = float(benchmark.loc[current_date])
        turnover = compute_turnover(weights, previous_weights)
        transaction_cost = turnover * config.cost_bps / 10_000.0
        ic = float(
            eligible_snapshot[config.score_column].rank().corr(
                eligible_snapshot["forward_return"].rank()
            )
        )
        weighted_snapshot = eligible_snapshot.assign(weight=eligible_snapshot["ticker"].map(weights).fillna(0.0))
        selected = weighted_snapshot.loc[weighted_snapshot["weight"] != 0.0].copy()
        execution_frame, execution_summary = simulate_execution(selected, date=current_date)
        execution_rows.extend(execution_frame.to_dict(orient="records"))
        execution_shortfall = float(execution_summary["implementation_shortfall_return"])
        net_return = realized - transaction_cost - execution_shortfall
        gross_exposure = float(weights.abs().sum())
        net_exposure = float(weights.sum())
        capacity_proxy = float((selected["weight"].abs() * selected["dollar_volume"]).sum()) if not selected.empty else 0.0
        max_name_weight = float(selected["weight"].abs().max()) if not selected.empty else 0.0

        exposure_rows.append(
            {
                "date": current_date,
                "value": float(
                    (eligible_snapshot["ticker"].map(weights).fillna(0.0) * eligible_snapshot["book_to_price_z"]).sum()
                ),
                "quality": float(
                    (eligible_snapshot["ticker"].map(weights).fillna(0.0) * eligible_snapshot["quality_z"]).sum()
                ),
                "momentum": float(
                    (eligible_snapshot["ticker"].map(weights).fillna(0.0) * eligible_snapshot["momentum_63_z"]).sum()
                ),
                "stability": float(
                    (eligible_snapshot["ticker"].map(weights).fillna(0.0) * eligible_snapshot["stability_z"]).sum()
                ),
                "beta": float((eligible_snapshot["ticker"].map(weights).fillna(0.0) * eligible_snapshot["beta_z"]).sum()),
            }
        )

        sector_tilts = (
            eligible_snapshot.assign(weight=eligible_snapshot["ticker"].map(weights).fillna(0.0))
            .groupby("sector")["weight"]
            .sum()
        )
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
                "execution_shortfall": execution_shortfall,
                "gross_exposure": gross_exposure,
                "net_exposure": net_exposure,
                "capacity_proxy": capacity_proxy,
                "max_name_weight": max_name_weight,
                "average_participation_rate": execution_summary["average_participation_rate"],
                "average_slippage_bps": execution_summary["average_slippage_bps"],
                "average_fill_ratio": execution_summary["average_fill_ratio"],
                "stressed_trade_count": execution_summary["stressed_trade_count"],
                "universe_size": int(len(snapshot)),
                "eligible_universe": int(universe_audit["eligible_universe"]),
                "universe_attrition": float(universe_audit["attrition_ratio"]),
            }
        )
        previous_weights = weights

    periods = pd.DataFrame(period_rows)
    exposures = pd.DataFrame(exposure_rows)
    holdings = pd.DataFrame(holdings_rows)
    execution_profile = pd.DataFrame(execution_rows)
    universe_audit_frame = pd.DataFrame(universe_audit_rows)
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
        "average_execution_shortfall": float(periods["execution_shortfall"].mean()),
        "average_gross_exposure": float(periods["gross_exposure"].mean()),
        "average_net_exposure": float(periods["net_exposure"].mean()),
        "median_capacity_proxy": float(periods["capacity_proxy"].median()),
        "max_name_weight": float(periods["max_name_weight"].max()),
        "average_participation_rate": float(periods["average_participation_rate"].mean()),
        "average_slippage_bps": float(periods["average_slippage_bps"].mean()),
        "average_fill_ratio": float(periods["average_fill_ratio"].mean()),
        "average_universe_attrition": float(periods["universe_attrition"].mean()),
        "median_eligible_universe": float(periods["eligible_universe"].median()),
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
        "execution_profile": execution_profile,
        "universe_audit": universe_audit_frame,
        "macro": macro,
    }
