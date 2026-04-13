from src.attribution import build_attribution
from src.lab import get_scenario_config, run_lab_scenario
from src.lineage import build_lineage_record
from src.platform import build_platform_summary, get_research_platform
from src.validation import build_validation_report


def test_research_pipeline_includes_lineage_validation_and_attribution():
    report = run_lab_scenario("quality_value_sector_neutral", seed=21)
    scenario = get_scenario_config("quality_value_sector_neutral")
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

    assert report["summary"]["period_count"] > 0
    assert report["summary"]["rebalance_count"] > 0
    assert "sector" in report["holdings"].columns
    assert validation["gates"]
    assert attribution["factor_contributions"]
    assert lineage["config_fingerprint"]
    assert platform_summary["research_readiness"] >= 0


def test_platform_snapshot_has_expected_components():
    platform = get_research_platform()

    assert len(platform["components"]) >= 5
    assert "turnover_budget" in platform["validation_gates"]
