from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _line_chart_svg(frame: pd.DataFrame, columns: list[str], title: str) -> str:
    width = 760
    height = 280
    margin = 36
    colors = ["#0f766e", "#1d4ed8", "#dc2626", "#f59e0b"]

    numeric = frame[columns].astype(float)
    minimum = float(numeric.min().min())
    maximum = float(numeric.max().max())
    if minimum == maximum:
        maximum = minimum + 1.0

    def scale_x(index: int) -> float:
        denominator = max(len(frame) - 1, 1)
        return margin + (width - margin * 2) * index / denominator

    def scale_y(value: float) -> float:
        return height - margin - (value - minimum) / (maximum - minimum) * (height - margin * 2)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc" rx="20"/>',
        f'<text x="{margin}" y="28" font-size="18" font-family="Arial" fill="#0f172a">{title}</text>',
    ]
    for idx, column in enumerate(columns):
        points = " ".join(
            f"{scale_x(row_idx):.2f},{scale_y(float(value)):.2f}"
            for row_idx, value in enumerate(frame[column].tolist())
        )
        parts.append(
            f'<polyline fill="none" stroke="{colors[idx % len(colors)]}" stroke-width="3" points="{points}"/>'
        )
        parts.append(
            f'<text x="{width - 180}" y="{32 + idx * 20}" font-size="12" font-family="Arial" fill="{colors[idx % len(colors)]}">{column}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _bar_chart_svg(series: pd.Series, title: str) -> str:
    width = 760
    height = 280
    margin = 40
    values = series.astype(float)
    maximum = max(abs(float(values.min())), abs(float(values.max())), 1e-6)
    bar_width = (width - margin * 2) / max(len(series), 1)
    baseline = height / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc" rx="20"/>',
        f'<text x="{margin}" y="28" font-size="18" font-family="Arial" fill="#0f172a">{title}</text>',
        f'<line x1="{margin}" y1="{baseline}" x2="{width - margin}" y2="{baseline}" stroke="#94a3b8" stroke-width="1"/>',
    ]
    for idx, (label, value) in enumerate(values.items()):
        left = margin + idx * bar_width + 6
        scaled_height = (abs(float(value)) / maximum) * (height / 2 - margin)
        top = baseline - scaled_height if value >= 0 else baseline
        color = "#2563eb" if value >= 0 else "#dc2626"
        parts.append(
            f'<rect x="{left:.2f}" y="{top:.2f}" width="{max(bar_width - 12, 8):.2f}" height="{scaled_height:.2f}" fill="{color}" rx="6"/>'
        )
        parts.append(
            f'<text x="{left:.2f}" y="{height - 18}" font-size="11" font-family="Arial" fill="#334155">{label}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def write_artifacts(output_dir: str | Path, report: dict[str, object]) -> dict[str, str]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    summary = report["summary"]
    equity_curve = report["equity_curve"]
    factor_exposures = report["factor_exposures"]
    holdings = report["holdings"]
    periods = report["period_returns"]

    report_path = path / "report.json"
    report_payload = {
        "summary": summary,
        "period_returns": periods.to_dict(orient="records"),
        "equity_curve": equity_curve.to_dict(orient="records"),
        "factor_exposures": factor_exposures.to_dict(orient="records"),
        "holdings": holdings.to_dict(orient="records"),
    }
    report_path.write_text(json.dumps(report_payload, indent=2, default=str))

    summary_path = path / "summary.md"
    summary_path.write_text(
        "\n".join(
            [
                f"# {summary['scenario_name']}",
                "",
                f"- Annualized return: {summary['annualized_return']:.2%}",
                f"- Annualized volatility: {summary['annualized_volatility']:.2%}",
                f"- Sharpe ratio: {summary['sharpe_ratio']:.2f}",
                f"- Max drawdown: {summary['max_drawdown']:.2%}",
                f"- Alpha annualized: {summary['alpha_annualized']:.2%}",
                f"- Average turnover: {summary['average_turnover']:.2f}",
            ]
        )
    )

    (path / "equity_curve.svg").write_text(
        _line_chart_svg(equity_curve, ["strategy_equity", "benchmark_equity"], "Strategy vs Benchmark Equity")
    )
    (path / "drawdown.svg").write_text(_line_chart_svg(equity_curve, ["drawdown"], "Drawdown Profile"))
    exposure_means = factor_exposures.drop(columns=["date"]).mean()
    (path / "factor_exposures.svg").write_text(_bar_chart_svg(exposure_means, "Average Factor Exposures"))

    latest_tilts = (
        holdings.loc[holdings["ticker"].str.startswith("Sector::")]
        .sort_values("date")
        .groupby("ticker")
        .tail(1)
        .set_index("ticker")["weight"]
    )
    latest_tilts.index = latest_tilts.index.str.replace("Sector::", "", regex=False)
    (path / "sector_tilts.svg").write_text(_bar_chart_svg(latest_tilts, "Latest Sector Tilts"))

    holdings.loc[~holdings["ticker"].str.startswith("Sector::")].to_csv(path / "holdings.csv", index=False)
    periods.to_csv(path / "period_returns.csv", index=False)

    manifest = {
        "files": [
            "report.json",
            "summary.md",
            "equity_curve.svg",
            "drawdown.svg",
            "factor_exposures.svg",
            "sector_tilts.svg",
            "holdings.csv",
            "period_returns.csv",
        ]
    }
    (path / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return {name: str(path / name) for name in manifest["files"] + ["manifest.json"]}
