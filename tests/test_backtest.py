from src.backtest import run_walk_forward_backtest
from src.factors import build_synthetic_panel, compute_factor_scores


def test_factor_scores_include_composite_score():
    prices, fundamentals = build_synthetic_panel()
    scores = compute_factor_scores(prices, fundamentals)

    assert "composite_score" in scores.columns
    assert not scores.empty


def test_backtest_produces_spread_returns():
    results = run_walk_forward_backtest()

    assert not results.empty
    assert "spread_return" in results.columns
