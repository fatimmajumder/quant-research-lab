from __future__ import annotations

import numpy as np
import pandas as pd


def build_synthetic_panel(periods: int = 180, assets: int = 24, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    tickers = [f"Asset_{idx:02d}" for idx in range(assets)]
    dates = pd.date_range("2024-01-01", periods=periods, freq="B")

    returns = rng.normal(0.0006, 0.015, size=(periods, assets))
    prices = 100 * (1 + returns).cumprod(axis=0)
    fundamentals = pd.DataFrame(
        {
            "ticker": tickers,
            "book_to_price": rng.normal(0.7, 0.15, size=assets),
            "quality": rng.normal(0.0, 1.0, size=assets),
        }
    )

    price_frame = pd.DataFrame(prices, index=dates, columns=tickers)
    return price_frame, fundamentals


def compute_factor_scores(price_frame: pd.DataFrame, fundamentals: pd.DataFrame) -> pd.DataFrame:
    momentum = price_frame.pct_change(20).iloc[-1]
    volatility = price_frame.pct_change().rolling(20).std().iloc[-1]

    scores = fundamentals.set_index("ticker").copy()
    scores["momentum"] = momentum
    scores["stability"] = -volatility

    z_scores = (scores - scores.mean()) / scores.std(ddof=0)
    z_scores["composite_score"] = z_scores[["book_to_price", "quality", "momentum", "stability"]].mean(axis=1)
    return z_scores.sort_values("composite_score", ascending=False)
