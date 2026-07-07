from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
Q3 = ROOT / "questions" / "q3"


def test_q3_precheck_generates_no_wind_feasibility_table() -> None:
    result = subprocess.run(
        [sys.executable, "questions/q3/scripts/precheck.py", "--config", "configs/default.yaml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    table_path = Q3 / "artifacts" / "tables" / "baseline_feasibility.csv"
    assert table_path.exists()
    table = pd.read_csv(table_path)
    assert {"configured_wind", "no_wind"}.issubset(set(table["wind_model"]))
    assert (table["target_distance_m"] == table["target_distance_m"].iloc[0]).all()
    assert (table["final_distance_error_m"].abs() < 1.0).all()
    assert (table["fuel_integral_error_kg"].abs() < 0.05).all()
    assert table["terminal_mass_feasible"].dtype == bool
    assert table["baseline_feasible"].dtype == bool
