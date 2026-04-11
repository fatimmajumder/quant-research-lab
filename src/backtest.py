from __future__ import annotations

import pandas as pd

from src.factors import build_synthetic_panel, compute_factor_scores


def run_walk_forward_backtest(seed: int = 7) -> pd.DataFrame:
    prices, fundamentals = build_synthetic_panel(seed=seed)
    forward_returns = prices.pct_change(5).shift(-5)

    snapshots = []
    for end_idx in range(60, len(prices) - 5, 20):
        window_prices = prices.iloc[:end_idx]
        scores = compute_factor_scores(window_prices, fundamentals)
        long_names = scores.head(5).index
        short_names = scores.tail(5).index
        period_returns = forward_returns.iloc[end_idx]
        long_return = period_returns[long_names].mean()
        short_return = period_returns[short_names].mean()
        snapshots.append(
            {
                "date": prices.index[end_idx],
                "long_return": long_return,
                "short_return": short_return,
                "spread_return": long_return - short_return,
            }
        )

    return pd.DataFrame(snapshots)


if __name__ == "__main__":
    results = run_walk_forward_backtest()
    print(results.tail())
    print("Average spread return:", round(results["spread_return"].mean(), 4))
