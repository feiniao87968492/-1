from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
Q3 = ROOT / "questions" / "q3"


def test_q3_no_wind_feasibility_gate_reports_mass_slack() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "questions/q3/scripts/solve_feasibility_no_wind.py",
            "--config",
            "configs/default.yaml",
            "--nodes",
            "21",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    table_path = Q3 / "artifacts" / "tables" / "no_wind_feasibility_gate.csv"
    trajectory_path = Q3 / "artifacts" / "tables" / "no_wind_feasibility_trajectory.csv"
    assert table_path.exists()
    assert trajectory_path.exists()

    summary = pd.read_csv(table_path)
    assert len(summary) == 1
    row = summary.iloc[0]
    assert row["wind_model"] == "no_wind"
    assert row["terminal_mass_shortfall_kg"] >= 0.0
    assert row["terminal_mass_shortfall_kg"] <= row["fixed_path_mass_shortfall_kg"]
    assert abs(row["fixed_path_mass_shortfall_kg"] - 836.526) < 0.01
    assert abs(row["terminal_height_error_m"]) < 1.0e-6
    assert abs(row["terminal_speed_error_mps"]) < 1.0e-6
    assert row["max_nonrelaxed_constraint_violation"] < 1.0e-8
    assert row["integration_consistency_residual"] < 1.0e-5
    assert row["solver_status"] in {"feasible", "needs_relaxation"}
    for column in [
        "min_height_m",
        "max_height_m",
        "min_airspeed_mps",
        "max_airspeed_mps",
        "min_thrust_n",
        "max_thrust_n",
        "min_gamma_rad",
        "max_gamma_rad",
        "max_mach",
        "min_cl",
        "max_cl",
        "height_margin_min_m",
        "airspeed_margin_min_mps",
        "thrust_margin_min_n",
        "gamma_margin_min_rad",
        "mach_margin_min",
    ]:
        assert column in summary.columns
        assert pd.notna(row[column])

    trajectory = pd.read_csv(trajectory_path)
    assert {"distance_m", "height_m", "airspeed_mps", "mass_kg", "time_s"}.issubset(
        trajectory.columns
    )
    assert trajectory["distance_m"].is_monotonic_increasing
