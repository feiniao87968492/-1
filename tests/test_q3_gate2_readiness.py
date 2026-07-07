from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_q3_smooth_atmosphere_is_hydrostatic_and_continuous() -> None:
    sys.path.insert(0, str(ROOT / "questions" / "q3" / "scripts"))
    from smooth_atmosphere import atmosphere, hydrostatic_residual

    for height_m in [10950.0, 11000.0, 11050.0]:
        temperature_k, density_kgm3, sound_speed_mps, pressure_pa = atmosphere(height_m)
        assert temperature_k > 0.0
        assert density_kgm3 > 0.0
        assert sound_speed_mps > 0.0
        assert pressure_pa > 0.0
        assert hydrostatic_residual(height_m) < 1.0e-6

    dh = 0.01
    t_slope_left = (atmosphere(11000.0)[0] - atmosphere(11000.0 - dh)[0]) / dh
    t_slope_right = (atmosphere(11000.0 + dh)[0] - atmosphere(11000.0)[0]) / dh
    assert abs(t_slope_left - t_slope_right) < 1.0e-5


def test_q3_gate2_config_and_manifest_are_explicit() -> None:
    config = yaml.safe_load((ROOT / "configs/default.yaml").read_text(encoding="utf-8"))
    gate = config["q3_optimal_control"]["feasibility_gate"]
    assert gate["slack_smoothing_tolerance_kg"] < gate["pass_criteria"]["terminal_mass_shortfall_kg"]
    assert gate["pass_criteria"]["constraint_violation_scale"] == "nondimensional"
    assert gate["atmosphere_smoothing_state"] == "temperature_only_hydrostatic_pressure"

    manifest = yaml.safe_load((ROOT / "questions/q3/manifest.yaml").read_text(encoding="utf-8"))
    assert (
        manifest["entrypoints"]["feasibility_collocation_no_wind"]
        == "questions/q3/scripts/solve_feasibility_collocation_no_wind.py"
    )
    assert "collocation_feasibility" in manifest["quality_gates"]
    assert "feasibility_collocation_summary" in manifest["outputs"]


def test_q3_collocation_gate_dry_run_exports_readiness_tables() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "questions/q3/scripts/solve_feasibility_collocation_no_wind.py",
            "--config",
            "configs/default.yaml",
            "--nodes",
            "21",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    summary_path = ROOT / "questions/q3/artifacts/tables/no_wind_collocation_gate.csv"
    trajectory_path = ROOT / "questions/q3/artifacts/tables/no_wind_collocation_trajectory.csv"
    sensitivity_path = ROOT / "questions/q3/artifacts/tables/no_wind_hmax_sensitivity.csv"
    assert summary_path.exists()
    assert trajectory_path.exists()
    assert sensitivity_path.exists()

    summary = pd.read_csv(summary_path)
    row = summary.iloc[0]
    assert row["method"] == "range_domain_collocation_readiness_dry_run"
    assert row["solver_status"] == "dry_run_not_optimized"
    assert row["atmosphere_model"] == "C1_temperature_hydrostatic_pressure"
    assert row["max_scaled_constraint_violation"] >= 0.0
    assert row["max_midpoint_height_violation_m"] >= 0.0

    sensitivity = pd.read_csv(sensitivity_path)
    assert set(sensitivity["h_max_m"]) == {10950.0, 11500.0, 12000.0, 12500.0}
