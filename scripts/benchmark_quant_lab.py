from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.attribution import build_attribution
from src.lab import SCENARIOS, get_scenario_config, run_lab_scenario
from src.lineage import build_lineage_record
from src.platform import build_platform_summary, get_research_platform
from src.validation import build_validation_report


EXAMPLES_DIR = ROOT / "examples"


def main() -> None:
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    scoreboard = []
    best_payload = None
    best_sharpe = float("-inf")

    for scenario_id in SCENARIOS:
        report = run_lab_scenario(scenario_id, seed=21)
        scenario = get_scenario_config(scenario_id)
        validation = build_validation_report(
            report["summary"],
            report["factor_exposures"],
            report["holdings"],
            report["period_returns"],
        )
        attribution = build_attribution(
            report["period_returns"],
            report["factor_exposures"],
            report["holdings"],
        )
        lineage = build_lineage_record(scenario, "synthetic_us_equities", 21, report["summary"])
        platform_summary = build_platform_summary(report["summary"], lineage, validation, attribution)
        scoreboard.append(
            {
                "scenario_id": scenario_id,
                "scenario_name": report["summary"]["scenario_name"],
                "annualized_return": report["summary"]["annualized_return"],
                "sharpe_ratio": report["summary"]["sharpe_ratio"],
                "max_drawdown": report["summary"]["max_drawdown"],
                "research_readiness": platform_summary["research_readiness"],
                "validation_status": validation["overall_status"],
                "fingerprint": lineage["config_fingerprint"],
            }
        )
        if report["summary"]["sharpe_ratio"] > best_sharpe:
            best_sharpe = report["summary"]["sharpe_ratio"]
            best_payload = {
                "summary": report["summary"],
                "validation_report": validation,
                "attribution": attribution,
                "lineage": lineage,
                "platform_summary": platform_summary,
                "platform": get_research_platform(),
                "scoreboard": scoreboard,
            }

    (EXAMPLES_DIR / "sample_report.json").write_text(json.dumps(best_payload, indent=2, default=str))
    metrics_lines = ["# Quant Research Lab Sample Metrics", ""]
    for row in sorted(scoreboard, key=lambda item: item["sharpe_ratio"], reverse=True):
        metrics_lines.append(
            f"- {row['scenario_name']}: sharpe={row['sharpe_ratio']:.2f}, "
            f"return={row['annualized_return']:.2%}, readiness={row['research_readiness']:.1f}, "
            f"validation={row['validation_status']}"
        )
    (EXAMPLES_DIR / "sample_metrics.txt").write_text("\n".join(metrics_lines) + "\n")


if __name__ == "__main__":
    main()
