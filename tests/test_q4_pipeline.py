from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_q4_pipeline_exports_wind_optimal_and_strategy_comparison_tables() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "questions/q4/scripts/pipeline.py",
            "--config",
            "configs/default.yaml",
            "--nodes",
            "41",
            "--control-knots",
            "5",
            "--maxiter",
            "60",
            "--skip-beta-sensitivity",
            "--skip-range-extension",
            "--skip-extension-frameworks",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    results_path = ROOT / "questions/q4/artifacts/tables/wind_optimal_results.csv"
    comparison_path = ROOT / "questions/q4/artifacts/tables/strategy_comparison.csv"
    trajectory_path = ROOT / "questions/q4/artifacts/tables/wind_optimal_trajectory.csv"
    assert results_path.exists()
    assert comparison_path.exists()
    assert trajectory_path.exists()

    results = pd.read_csv(results_path)
    assert len(results) == 1
    row = results.iloc[0]
    assert row["artifact_id"] == "q4-T02"
    assert row["wind_model"] == "configured_wind"
    assert row["objective"] == "min_m0_minus_mf"
    assert row["claim_level"] == "locally_optimized_solution"
    assert row["validation_status"] == "passed"
    assert row["fuel_used_kg"] > 0.0
    assert row["terminal_mass_shortfall_kg"] <= 0.05
    assert row["terminal_height_error_m"] <= 0.1
    assert row["terminal_speed_error_mps"] <= 1.0e-3
    assert row["max_scaled_constraint_violation"] <= 1.0e-6
    assert row["fuel_identity_residual_kg"] <= 0.1

    comparison = pd.read_csv(comparison_path)
    assert set(comparison["artifact_id"]) == {"q4-T03"}
    assert set(comparison["strategy"]) == {"constant_speed_baseline", "configured_wind_optimal"}
    baseline = comparison.loc[comparison["strategy"] == "constant_speed_baseline"].iloc[0]
    optimum = comparison.loc[comparison["strategy"] == "configured_wind_optimal"].iloc[0]
    assert baseline["fixed_range_m"] == optimum["fixed_range_m"]
    assert optimum["fuel_used_kg"] < baseline["fuel_used_kg"]
    assert optimum["fuel_saving_vs_baseline_kg"] > 0.0
    assert optimum["fuel_saving_vs_baseline_pct"] > 0.0
    assert pd.notna(optimum["range_change_vs_q1_constant_speed_m"])

    trajectory = pd.read_csv(trajectory_path)
    assert len(trajectory) == 41
    for column in [
        "distance_m",
        "height_m",
        "airspeed_mps",
        "mass_kg",
        "time_s",
        "thrust_n",
        "gamma_rad",
        "groundspeed_mps",
        "scaled_constraint_violation",
    ]:
        assert column in trajectory.columns


def test_q4_pipeline_exports_beta_range_and_extension_tables() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "questions/q4/scripts/pipeline.py",
            "--config",
            "configs/default.yaml",
            "--nodes",
            "31",
            "--control-knots",
            "4",
            "--maxiter",
            "50",
            "--beta-factors",
            "0.9,1.0,1.1",
            "--range-factors",
            "1.0,1.03",
            "--sensitivity-maxiter",
            "30",
            "--range-maxiter",
            "30",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    beta_path = ROOT / "questions/q4/artifacts/tables/beta_sensitivity.csv"
    range_path = ROOT / "questions/q4/artifacts/tables/fixed_fuel_range.csv"
    extensions_path = ROOT / "questions/q4/artifacts/tables/extension_frameworks.csv"
    assert beta_path.exists()
    assert range_path.exists()
    assert extensions_path.exists()

    beta = pd.read_csv(beta_path)
    assert set(beta["artifact_id"]) == {"q4-T04"}
    assert set(beta["beta_factor"].round(2)) == {0.9, 1.0, 1.1}
    assert beta["reoptimization_performed"].all()
    assert "post_solution_metric_only" in beta.columns
    assert not beta["post_solution_metric_only"].any()
    nominal = beta.loc[beta["beta_factor"].round(2) == 1.0].iloc[0]
    assert nominal["validation_status"] == "passed"
    assert nominal["fuel_used_kg"] > 0.0
    assert nominal["fuel_delta_vs_nominal_kg"] == 0.0

    fixed_fuel = pd.read_csv(range_path)
    assert set(fixed_fuel["artifact_id"]) == {"q4-T06"}
    assert "estimated_fixed_fuel_range_m" in fixed_fuel.columns
    assert "range_gain_vs_fixed_range_m" in fixed_fuel.columns
    assert fixed_fuel["estimated_fixed_fuel_range_m"].iloc[0] >= fixed_fuel["fixed_range_m"].iloc[0]
    assert fixed_fuel["claim_level"].iloc[0] == "local_fixed_fuel_range_estimate"

    extensions = pd.read_csv(extensions_path)
    assert set(extensions["artifact_id"]) == {"q4-T05"}
    assert set(extensions["framework_id"]) == {
        "temperature_realtime_correction",
        "engine_installation_loss",
    }
    for column in ["model_change", "required_data", "validation_plan", "evidence_boundary"]:
        assert extensions[column].notna().all()


def test_q4_visualize_exports_paper_figure_bundles() -> None:
    pipeline = subprocess.run(
        [
            sys.executable,
            "questions/q4/scripts/pipeline.py",
            "--config",
            "configs/default.yaml",
            "--nodes",
            "31",
            "--control-knots",
            "4",
            "--maxiter",
            "50",
            "--beta-factors",
            "0.9,1.0,1.1",
            "--range-factors",
            "1.0,1.03",
            "--sensitivity-maxiter",
            "30",
            "--range-maxiter",
            "30",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert pipeline.returncode == 0, pipeline.stdout + pipeline.stderr

    result = subprocess.run(
        [sys.executable, "questions/q4/scripts/visualize.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    for stem in ["height_range_comparison", "profile_comparison", "beta_sensitivity"]:
        figure = ROOT / "questions/q4/artifacts/figures" / f"{stem}.png"
        data = ROOT / "questions/q4/artifacts/figure_data" / f"{stem}.csv"
        metadata = ROOT / "questions/q4/artifacts/figure_data" / f"{stem}.meta.json"
        assert figure.exists()
        assert figure.stat().st_size > 1000
        assert data.exists()
        assert metadata.exists()
        frame = pd.read_csv(data)
        assert not frame.empty
