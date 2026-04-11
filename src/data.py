from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import requests


SECTORS = [
    "Technology",
    "Financials",
    "Healthcare",
    "Industrials",
    "Energy",
    "Consumer",
    "Utilities",
    "Materials",
]


@dataclass(frozen=True)
class PublicDataset:
    dataset_id: str
    name: str
    description: str
    source_url: str
    cadence: str


PUBLIC_DATASETS = [
    PublicDataset(
        dataset_id="fama_french_daily_3_factor",
        name="Fama-French Daily 3 Factors",
        description="Daily market, SMB, and HML factor series from the Kenneth French data library.",
        source_url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_daily_CSV.zip",
        cadence="daily",
    ),
    PublicDataset(
        dataset_id="fama_french_daily_5_factor",
        name="Fama-French Daily 5 Factors",
        description="Daily five-factor research file for broad factor benchmarking.",
        source_url="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",
        cadence="daily",
    ),
    PublicDataset(
        dataset_id="fred_macro_core",
        name="FRED Macro Core",
        description="Treasury yield and policy-rate panel for regime and carry overlays.",
        source_url="https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10,DFF,UNRATE",
        cadence="daily",
    ),
    PublicDataset(
        dataset_id="fred_market_proxies",
        name="FRED Market Proxies",
        description="S&P 500 and VIX proxy series for quick equity and volatility ingest smoke tests.",
        source_url="https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500,VIXCLS",
        cadence="daily",
    ),
]


def get_public_datasets() -> list[dict[str, str]]:
    return [dataset.__dict__.copy() for dataset in PUBLIC_DATASETS]


def build_synthetic_market_panel(
    periods: int = 504,
    assets: int = 48,
    seed: int = 21,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-03", periods=periods, freq="B")
    tickers = [f"Asset_{idx:03d}" for idx in range(assets)]
    sector_index = np.arange(assets) % len(SECTORS)
    sectors = np.array([SECTORS[idx] for idx in sector_index])

    factor_names = ["market", "value", "quality", "momentum", "low_vol", "macro"]
    book_to_price_base = rng.normal(0.75, 0.18, size=assets)
    quality_base = rng.normal(0.0, 1.0, size=assets)
    profitability_base = rng.normal(0.0, 0.8, size=assets)
    size_base = rng.normal(10.8, 0.55, size=assets)
    liquidity_base = rng.normal(0.0, 1.0, size=assets)

    def standardize(values: np.ndarray) -> np.ndarray:
        return (values - values.mean()) / values.std(ddof=0)

    value_signal = standardize(book_to_price_base)
    quality_signal = standardize(0.65 * quality_base + 0.35 * profitability_base)
    size_signal = standardize(size_base)
    liquidity_signal = standardize(liquidity_base)

    exposures = pd.DataFrame(
        {
            "ticker": tickers,
            "sector": sectors,
            "value_beta": 0.80 * value_signal + rng.normal(0.0, 0.28, size=assets),
            "quality_beta": 0.75 * quality_signal + rng.normal(0.0, 0.24, size=assets),
            "momentum_beta": 0.45 * quality_signal + 0.35 * liquidity_signal + rng.normal(0.0, 0.30, size=assets),
            "low_vol_beta": 0.50 * quality_signal - 0.30 * size_signal + rng.normal(0.0, 0.22, size=assets),
            "macro_beta": 0.35 * size_signal - 0.40 * liquidity_signal + rng.normal(0.0, 0.25, size=assets),
            "book_to_price_base": book_to_price_base,
            "quality_base": quality_base,
            "profitability_base": profitability_base,
            "size_base": size_base,
            "liquidity_base": liquidity_base,
        }
    )

    growth = np.zeros(periods)
    inflation = np.zeros(periods)
    stress = np.zeros(periods)
    policy_rate = np.zeros(periods)
    term_spread = np.zeros(periods)

    for idx in range(1, periods):
        growth[idx] = 0.96 * growth[idx - 1] + rng.normal(0.0, 0.08)
        inflation[idx] = 0.93 * inflation[idx - 1] + rng.normal(0.0, 0.06)
        stress[idx] = max(0.0, 0.85 * stress[idx - 1] + rng.normal(0.02, 0.08))
        policy_rate[idx] = 0.98 * policy_rate[idx - 1] + rng.normal(0.01, 0.04)
        term_spread[idx] = 0.92 * term_spread[idx - 1] + rng.normal(0.0, 0.05)

    macro = pd.DataFrame(
        {
            "date": dates,
            "growth": growth,
            "inflation": inflation,
            "stress": stress,
            "policy_rate": 3.25 + policy_rate,
            "term_spread": 1.00 + term_spread,
        }
    )
    macro["macro_regime"] = (
        0.45 * macro["growth"]
        - 0.30 * macro["inflation"]
        - 0.55 * macro["stress"]
        + 0.25 * macro["term_spread"]
    )

    factor_matrix = np.column_stack(
        [
            rng.normal(0.00045 + 0.00010 * growth - 0.00025 * stress, 0.008, size=periods),
            rng.normal(0.00026 - 0.00006 * stress + 0.00005 * inflation, 0.0042, size=periods),
            rng.normal(0.00024 + 0.00012 * stress, 0.0031, size=periods),
            rng.normal(0.00028 + 0.00016 * growth - 0.00005 * stress, 0.0038, size=periods),
            rng.normal(0.00018 + 0.00015 * stress, 0.0026, size=periods),
            rng.normal(0.00012 + 0.00012 * macro["macro_regime"], 0.0032, size=periods),
        ]
    )
    factor_returns = pd.DataFrame(factor_matrix, columns=factor_names, index=dates)

    sector_noise = rng.normal(0.0, 0.0025, size=(periods, len(SECTORS)))
    idiosyncratic = rng.normal(0.0, 0.010, size=(periods, assets))
    base_exposure_matrix = exposures[
        ["value_beta", "quality_beta", "momentum_beta", "low_vol_beta", "macro_beta"]
    ].to_numpy()
    market_vector = factor_returns["market"].to_numpy()[:, None]
    style_vector = factor_returns[["value", "quality", "momentum", "low_vol", "macro"]].to_numpy()
    returns = (
        market_vector
        + style_vector @ base_exposure_matrix.T
        + sector_noise[:, sector_index]
        + idiosyncratic
        + 0.00008
    )
    prices = 100.0 * np.cumprod(1.0 + returns, axis=0)

    rows: list[pd.DataFrame] = []
    shares_outstanding = np.exp(exposures["size_base"].to_numpy()) * 2_500
    for idx, current_date in enumerate(dates):
        drift = idx / max(periods - 1, 1)
        current = exposures[["ticker", "sector"]].copy()
        current["date"] = current_date
        current["return"] = returns[idx]
        current["price"] = prices[idx]
        current["book_to_price"] = exposures["book_to_price_base"] + 0.03 * np.sin(drift * np.pi * 4)
        current["quality"] = exposures["quality_base"] + 0.20 * growth[idx] - 0.15 * stress[idx]
        current["profitability"] = exposures["profitability_base"] + 0.10 * growth[idx]
        current["beta"] = 1.0 + 0.25 * exposures["macro_beta"] - 0.10 * exposures["low_vol_beta"]
        current["size"] = exposures["size_base"] + 0.015 * idx
        current["liquidity"] = exposures["liquidity_base"] - 0.10 * stress[idx]
        current["market_cap"] = current["price"] * shares_outstanding
        current["dollar_volume"] = current["market_cap"] * (0.0025 + 0.001 * np.abs(current["return"]))
        rows.append(current)

    panel = pd.concat(rows, ignore_index=True)
    return panel, macro


def download_public_dataset(dataset_id: str, output_dir: str | Path) -> dict[str, object]:
    dataset = next((item for item in PUBLIC_DATASETS if item.dataset_id == dataset_id), None)
    if dataset is None:
        raise ValueError(f"Unknown dataset: {dataset_id}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    target_path = output_path / f"{dataset_id}.csv"

    if dataset_id.startswith("fama_french"):
        response = requests.get(dataset.source_url, timeout=30)
        response.raise_for_status()
        with ZipFile(BytesIO(response.content)) as archive:
            raw_name = archive.namelist()[0]
            raw_text = archive.read(raw_name).decode("latin-1")

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        header = None
        records: list[str] = []
        for line in lines:
            if line.startswith(","):
                continue
            if header is None and "Mkt-RF" in line:
                header = line.replace(" ", "")
                continue
            if header is not None:
                if not line[0].isdigit():
                    break
                records.append(line)

        csv_text = header + "\n" + "\n".join(records)
        frame = pd.read_csv(BytesIO(csv_text.encode()))
        frame = frame.rename(columns={frame.columns[0]: "date"})
        frame["date"] = pd.to_datetime(frame["date"], format="%Y%m%d")
        for column in frame.columns[1:]:
            frame[column] = frame[column].astype(float) / 100.0
    else:
        response = requests.get(dataset.source_url, timeout=30)
        response.raise_for_status()
        frame = pd.read_csv(BytesIO(response.content))
        first_column = frame.columns[0]
        frame = frame.rename(columns={first_column: "date"})
        frame["date"] = pd.to_datetime(frame["date"])

    frame.to_csv(target_path, index=False)
    return {
        "dataset_id": dataset_id,
        "output_path": str(target_path),
        "rows": int(len(frame)),
        "columns": list(frame.columns),
    }
