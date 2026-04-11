from __future__ import annotations

import streamlit as st

from src.backtest import run_walk_forward_backtest
from src.factors import build_synthetic_panel, compute_factor_scores

st.set_page_config(page_title="Quant Research Lab", layout="wide")
st.title("Quant Research Lab")
st.caption("Public demo of a leakage-aware factor research workflow.")

prices, fundamentals = build_synthetic_panel()
scores = compute_factor_scores(prices, fundamentals)
results = run_walk_forward_backtest()

left, right = st.columns((1.2, 1.0))

with left:
    st.subheader("Top composite factor scores")
    st.dataframe(scores.head(10), use_container_width=True)

with right:
    st.subheader("Walk-forward spread returns")
    st.line_chart(results.set_index("date")["spread_return"])

st.subheader("Backtest snapshots")
st.dataframe(results, use_container_width=True)
