# Quant Research Lab

Public-facing research-platform showcase inspired by the systems work I led at Algory Capital.

## Project framing

This repo is an original demo of a leakage-aware quant research workflow: ingest data, build factors, run walk-forward backtests, inspect diagnostics, and produce clear tearsheets.

## What it demonstrates

- factor pipeline structure
- walk-forward validation discipline
- exposure-aware portfolio construction scaffolding
- reproducible experiment logging
- dashboard-first research ergonomics

## Stack

- Python
- pandas / NumPy
- Streamlit
- PostgreSQL-style storage patterns
- GitHub Actions-style reproducibility mindset

## Goals

- make research infrastructure visible as a real engineering discipline
- show how I think about leakage, point-in-time correctness, and research velocity
- give recruiters something more concrete than a bullet point

## Planned repository structure

- `app.py` for a simple research dashboard
- `src/factors.py`
- `src/backtest.py`
- `src/portfolio.py`
- `requirements.txt`

## Resume-aligned highlights

- built the research stack for a 30+ member investment organization
- increased strategy research throughput by 6.8x
- reduced new-analyst ramp from about 6 weeks to 8 days
