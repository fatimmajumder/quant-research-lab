from __future__ import annotations

from src.backtest import ScenarioConfig, run_backtest


SCENARIOS = {
    "quality_value_sector_neutral": ScenarioConfig(
        scenario_id="quality_value_sector_neutral",
        name="Quality + Value Sector Neutral",
        description="Balanced cross-sectional sleeve that sector-neutralizes value and quality before building a 10x10 long-short book.",
        score_column="quality_value_score",
        top_n=10,
        holding_period=21,
        cost_bps=12.0,
        portfolio_style="equal_weight",
        sector_neutral=True,
    ),
    "momentum_regime_overlay": ScenarioConfig(
        scenario_id="momentum_regime_overlay",
        name="Momentum with Regime Overlay",
        description="Momentum portfolio that blends 63-day trend with a macro regime score and volatility-aware sizing.",
        score_column="momentum_regime_score",
        top_n=8,
        holding_period=21,
        cost_bps=16.0,
        portfolio_style="risk_scaled",
        sector_neutral=True,
    ),
    "defensive_quality_low_vol": ScenarioConfig(
        scenario_id="defensive_quality_low_vol",
        name="Defensive Quality / Low Vol",
        description="Defensive sleeve for higher-stress environments with a quality and stability bias.",
        score_column="defensive_score",
        top_n=10,
        holding_period=21,
        cost_bps=10.0,
        portfolio_style="risk_scaled",
        sector_neutral=True,
    ),
    "earnings_revision_quality": ScenarioConfig(
        scenario_id="earnings_revision_quality",
        name="Earnings Revision + Quality",
        description="Research sleeve that blends revision-like momentum proxies with quality and profitability controls.",
        score_column="earnings_revision_score",
        top_n=10,
        holding_period=21,
        cost_bps=14.0,
        portfolio_style="risk_scaled",
        sector_neutral=True,
    ),
    "liquidity_resilience_barbell": ScenarioConfig(
        scenario_id="liquidity_resilience_barbell",
        name="Liquidity Resilience Barbell",
        description="Barbell sleeve balancing resilient quality names against stressed-but-cheap opportunities with liquidity guards.",
        score_column="liquidity_resilience_score",
        top_n=8,
        holding_period=15,
        cost_bps=18.0,
        portfolio_style="risk_scaled",
        sector_neutral=True,
    ),
}


def list_scenarios() -> list[dict[str, object]]:
    return [
        {
            "scenario_id": scenario.scenario_id,
            "name": scenario.name,
            "description": scenario.description,
            "score_column": scenario.score_column,
            "top_n": scenario.top_n,
            "holding_period": scenario.holding_period,
            "cost_bps": scenario.cost_bps,
            "portfolio_style": scenario.portfolio_style,
            "sector_neutral": scenario.sector_neutral,
        }
        for scenario in SCENARIOS.values()
    ]


def run_lab_scenario(scenario_id: str, seed: int = 21) -> dict[str, object]:
    scenario = SCENARIOS[scenario_id]
    return run_backtest(scenario, seed=seed)


def get_scenario_config(scenario_id: str) -> dict[str, object]:
    scenario = SCENARIOS[scenario_id]
    return {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "description": scenario.description,
        "score_column": scenario.score_column,
        "top_n": scenario.top_n,
        "holding_period": scenario.holding_period,
        "cost_bps": scenario.cost_bps,
        "portfolio_style": scenario.portfolio_style,
        "sector_neutral": scenario.sector_neutral,
    }
