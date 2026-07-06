from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
Q1 = ROOT / "questions" / "q1"


def test_confirmed_wind_formula_uses_user_coefficient() -> None:
    sys.path.insert(0, str(Q1 / "scripts"))
    from atmosphere import wind_speed_mps

    assert wind_speed_mps(10_000.0) == pytest.approx(20.0)
    assert wind_speed_mps(9_500.0) == pytest.approx(27.5)


def test_strategy_outputs_required_columns_and_physical_invariants() -> None:
    sys.path.insert(0, str(Q1 / "scripts"))
    from simulate import run_strategies

    outputs = run_strategies()
    required = {
        "time_s",
        "distance_m",
        "mass_kg",
        "height_m",
        "airspeed_mps",
        "groundspeed_mps",
        "mach",
        "density_kgm3",
        "lift_N",
        "drag_N",
        "thrust_N",
        "fuel_flow_kgs",
        "climb_rate_mps",
        "energy_residual",
        "lift_balance_residual",
    }

    assert set(outputs) == {"constant_speed", "constant_mach"}
    for frame in outputs.values():
        assert required.issubset(frame.columns)
        assert len(frame) > 10
        assert frame["mass_kg"].iloc[0] == pytest.approx(72450.0)
        assert frame["mass_kg"].iloc[-1] == pytest.approx(62000.0, abs=2.0)
        assert frame["mass_kg"].is_monotonic_decreasing
        assert (frame["density_kgm3"] > 0).all()
        assert (frame["airspeed_mps"] > 0).all()
        assert (frame["groundspeed_mps"] > 0).all()
        assert frame["lift_balance_residual"].abs().max() < 1e-6
        assert frame["energy_residual"].abs().max() < 1e-6


def test_pipeline_generates_required_q1_artifacts() -> None:
    result = subprocess.run(
        [sys.executable, "questions/q1/scripts/pipeline.py", "--config", "configs/default.yaml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    expected = [
        ROOT / "artifacts/q1/data/constant_speed_profile.csv",
        ROOT / "artifacts/q1/data/constant_mach_profile.csv",
        ROOT / "artifacts/q1/data/strategy_comparison.csv",
        Q1 / "artifacts/tables/strategy_comparison.csv",
        Q1 / "artifacts/figures/height_time.png",
        Q1 / "artifacts/figure_data/height_time.csv",
        Q1 / "artifacts/figure_data/height_time.meta.json",
    ]
    missing = [path for path in expected if not path.exists()]
    assert not missing

    comparison = pd.read_csv(ROOT / "artifacts/q1/data/strategy_comparison.csv")
    assert set(comparison["strategy"]) == {"constant_speed", "constant_mach"}
    assert comparison["fuel_used_kg"].nunique() == 1
    assert comparison["fuel_used_kg"].iloc[0] == pytest.approx(10450.0)


def test_comparison_uses_time_weighted_trajectory_averages() -> None:
    sys.path.insert(0, str(Q1 / "scripts"))
    from aircraft_model import AircraftParameters
    from simulate import comparison_table

    frame = pd.DataFrame(
        {
            "time_s": [0.0, 1.0, 11.0],
            "distance_m": [0.0, 100.0, 200.0],
            "height_m": [0.0, 10.0, 20.0],
            "climb_rate_mps": [10.0, 10.0, 1.0],
            "groundspeed_mps": [100.0, 100.0, 10.0],
            "energy_residual": [0.0, 0.0, 0.0],
            "lift_balance_residual": [0.0, 0.0, 0.0],
        }
    )
    comparison = comparison_table({"synthetic": frame}, AircraftParameters())
    row = comparison.iloc[0]

    assert row["mean_climb_rate_mps"] == pytest.approx(20.0 / 11.0)
    assert row["mean_groundspeed_mps"] == pytest.approx(200.0 / 11.0)


def test_validation_checks_step_sensitivity_on_reported_metrics() -> None:
    subprocess.run(
        [sys.executable, "questions/q1/scripts/pipeline.py", "--config", "configs/default.yaml"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    validation = pd.read_csv(Q1 / "artifacts/tables/validation_summary.csv")
    checks = set(validation["check"])

    assert "step_sensitivity_final_time" in checks
    assert "step_sensitivity_final_distance" in checks
    assert "step_sensitivity_final_height" not in checks


def test_sensitivity_honors_configured_beta_perturbations(tmp_path: Path) -> None:
    config = yaml.safe_load((ROOT / "configs/default.yaml").read_text(encoding="utf-8"))
    config["validation"]["sensitivity_relative_changes"] = [-0.2, -0.1, 0.1, 0.2]
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "questions/q1/scripts/pipeline.py", "--config", str(config_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    sensitivity = pd.read_csv(Q1 / "artifacts/tables/sensitivity_summary.csv")
    scenarios = set(sensitivity["scenario"])
    assert {"beta_minus_20pct", "beta_minus_10pct", "beta_plus_10pct", "beta_plus_20pct"}.issubset(
        scenarios
    )
