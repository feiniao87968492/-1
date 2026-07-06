from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
Q2 = ROOT / "questions" / "q2"


def test_q2_pipeline_generates_fuel_path_artifacts() -> None:
    result = subprocess.run(
        [sys.executable, "questions/q2/scripts/pipeline.py", "--config", "configs/default.yaml"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    required = [
        ROOT / "artifacts/q2/data/q2_standard_profile.csv",
        ROOT / "artifacts/q2/data/q2_temperature_corrected_profile.csv",
        ROOT / "artifacts/q2/data/q2_fuel_summary.csv",
        Q2 / "artifacts/tables/fuel_summary.csv",
        Q2 / "artifacts/tables/validation_summary.csv",
        Q2 / "artifacts/figures/fuel_rate_path.png",
        Q2 / "artifacts/figure_data/fuel_rate_path.csv",
        Q2 / "artifacts/figure_data/fuel_rate_path.meta.json",
    ]
    assert not [path for path in required if not path.exists()]

    summary = pd.read_csv(ROOT / "artifacts/q2/data/q2_fuel_summary.csv")
    assert {"standard_isa", "temp_plus_10K"}.issubset(set(summary["scenario"]))
    assert (summary["fuel_used_kg"] > 0).all()
    assert (summary["final_distance_m"] > 199_000.0).all()
    assert (summary["final_distance_m"] < 202_000.0).all()


def test_q2_validation_contains_distance_and_temperature_checks() -> None:
    subprocess.run(
        [sys.executable, "questions/q2/scripts/pipeline.py", "--config", "configs/default.yaml"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    validation = pd.read_csv(Q2 / "artifacts/tables/validation_summary.csv")
    checks = set(validation["check"])
    assert "fixed_range_error" in checks
    assert "positive_fuel_rate" in checks
    assert "temperature_correction_effect" in checks
    assert validation["passed"].all()
