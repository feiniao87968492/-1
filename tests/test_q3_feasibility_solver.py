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
    assert row["terminal_mass_slack_kg"] >= 0.0
    assert row["terminal_mass_slack_kg"] <= row["fixed_path_mass_slack_kg"]
    assert abs(row["terminal_height_error_m"]) < 1.0e-6
    assert abs(row["terminal_speed_error_mps"]) < 1.0e-6
    assert row["max_abs_path_residual"] < 1.0e-5
    assert row["solver_status"] in {"feasible", "needs_relaxation"}

    trajectory = pd.read_csv(trajectory_path)
    assert {"distance_m", "height_m", "airspeed_mps", "mass_kg", "time_s"}.issubset(
        trajectory.columns
    )
    assert trajectory["distance_m"].is_monotonic_increasing
