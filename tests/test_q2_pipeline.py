from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
Q2 = ROOT / "questions" / "q2"
sys.path.insert(0, str(Q2 / "scripts"))

from fuel_path_model import Q2Parameters, atmosphere, isa_pressure_pa  # noqa: E402


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
    expected_scenarios = {
        "temp_minus_10K",
        "temp_minus_5K",
        "temp_minus_2K",
        "standard_isa",
        "temp_plus_2K",
        "temp_plus_5K",
        "temp_plus_10K",
    }
    assert expected_scenarios.issubset(set(summary["scenario"]))
    assert (ROOT / "artifacts/q2/data/q2_temperature_sensitivity.csv").exists()

    standard = pd.read_csv(ROOT / "artifacts/q2/data/q2_standard_profile.csv")
    for column in [
        "fuel_per_meter_kgpm",
        "cumulative_fuel_time_kg",
        "cumulative_fuel_path_kg",
        "path_integral_mass_kg",
    ]:
        assert column in standard.columns


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
    assert "hydrostatic_residual" in checks
    assert "time_path_integral_consistency" in checks
    assert "delta_zero_converges_to_isa" in checks
    assert "step_sensitivity" in checks
    assert "positive_negative_temperature_response" in checks
    assert validation["passed"].all()


def test_q2_temperature_offset_pressure_uses_hydrostatic_correction() -> None:
    height_m = 10_000.0
    temperature_0, density_0, sound_0, pressure_0 = atmosphere(height_m, temperature_offset_k=0.0)
    temperature_10, density_10, sound_10, pressure_10 = atmosphere(height_m, temperature_offset_k=10.0)

    assert pressure_0 == pytest.approx(isa_pressure_pa(height_m), rel=1e-12)
    assert pressure_10 != pytest.approx(isa_pressure_pa(height_m), rel=1e-6)
    assert temperature_10 > temperature_0
    assert sound_10 > sound_0
    assert density_10 != pytest.approx(density_0)

    params = Q2Parameters()
    dh = 0.1
    _, rho_mid, _, _ = atmosphere(height_m, temperature_offset_k=10.0)
    _, _, _, p_low = atmosphere(height_m - dh, temperature_offset_k=10.0)
    _, _, _, p_high = atmosphere(height_m + dh, temperature_offset_k=10.0)
    dp_dh = (p_high - p_low) / (2.0 * dh)
    residual = abs(dp_dh + rho_mid * params.g_mps2) / (rho_mid * params.g_mps2)
    assert residual < 1e-5


def test_q2_path_integral_matches_final_mass_loss() -> None:
    subprocess.run(
        [sys.executable, "questions/q2/scripts/pipeline.py", "--config", "configs/default.yaml"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    params = Q2Parameters()
    profile = pd.read_csv(ROOT / "artifacts/q2/data/q2_standard_profile.csv")
    final_loss = params.m0_kg - profile["mass_kg"].iloc[-1]
    time_integral = np.trapezoid(profile["fuel_flow_kgs"], profile["time_s"])
    path_integral = np.trapezoid(profile["fuel_per_meter_kgpm"], profile["distance_m"])
    assert time_integral == pytest.approx(final_loss, abs=1e-2)
    assert path_integral == pytest.approx(final_loss, abs=1e-2)
