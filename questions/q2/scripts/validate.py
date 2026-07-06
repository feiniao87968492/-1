#!/usr/bin/env python3
"""Validation and sensitivity analysis for q2."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [SRC, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from modeling_common.artifacts import save_table  # noqa: E402
from fuel_path_model import Q2Parameters, atmosphere, simulate_fixed_range, temperature_scenario_name  # noqa: E402


def _load_outputs(root: Path) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    data_dir = root / "artifacts" / "q2" / "data"
    summary = pd.read_csv(data_dir / "q2_fuel_summary.csv")
    profiles = {}
    for scenario in summary["scenario"]:
        scenario = str(scenario)
        profile_path = data_dir / f"q2_{scenario}_profile.csv"
        if scenario == "standard_isa":
            profile_path = data_dir / "q2_standard_profile.csv"
        elif scenario == "temp_plus_10K":
            profile_path = data_dir / "q2_temperature_corrected_profile.csv"
        profiles[scenario] = pd.read_csv(profile_path)
    return summary, profiles


def validation_summary(root: Path | None = None, params: Q2Parameters | None = None) -> pd.DataFrame:
    root = root or ROOT
    params = params or Q2Parameters()
    summary, profiles = _load_outputs(root)
    target_distance_m = float(summary.loc[summary["scenario"] == "standard_isa", "final_distance_m"].iloc[0])
    rows: list[dict[str, object]] = []
    for scenario, frame in profiles.items():
        final_distance = float(frame["distance_m"].iloc[-1])
        final_fuel = params.m0_kg - float(frame["mass_kg"].iloc[-1])
        time_integral = float(np.trapezoid(frame["fuel_flow_kgs"], frame["time_s"]))
        path_integral = float(np.trapezoid(frame["fuel_per_meter_kgpm"], frame["distance_m"]))
        max_integral_error = max(abs(time_integral - final_fuel), abs(path_integral - final_fuel))
        height_gradient = np.gradient(frame["height_m"].to_numpy(dtype=float), frame["distance_m"].to_numpy(dtype=float))
        max_path_angle = float(np.max(np.abs(height_gradient)))
        thrust_positive_min = float(frame["thrust_n"].min())
        smoothness = float(np.max(np.abs(np.diff(height_gradient)))) if len(height_gradient) > 1 else 0.0
        offset = float(summary.loc[summary["scenario"] == scenario, "temperature_offset_k"].iloc[0])
        hydrostatic_residual = _max_hydrostatic_residual(frame, offset, params)
        initial_state_error = max(
            abs(float(frame["height_m"].iloc[0]) - params.h0_m),
            abs(float(frame["airspeed_mps"].iloc[0]) - params.v0_mps),
            abs(float(frame["mass_kg"].iloc[0]) - params.m0_kg),
        )
        invalid_layer_count = int(
            ((frame["height_m"] <= 11_000.0) & (frame["atmosphere_layer"] != "troposphere")).sum()
            + ((frame["height_m"] > 11_000.0) & (frame["atmosphere_layer"] != "lower_stratosphere")).sum()
        )
        terminal_mass_margin = float(frame["mass_kg"].iloc[-1] - 62_000.0)
        rows.extend(
            [
                {
                    "check": "initial_state_match",
                    "scenario": scenario,
                    "value": initial_state_error,
                    "threshold": 1e-6,
                    "passed": bool(initial_state_error < 1e-6),
                    "notes": "initial height, airspeed, and mass match the problem statement state",
                },
                {
                    "check": "fixed_range_error",
                    "scenario": scenario,
                    "value": abs(final_distance - target_distance_m),
                    "threshold": 1.0,
                    "passed": bool(abs(final_distance - target_distance_m) < 1.0),
                    "notes": "terminal distance matches the ISA-to-terminal-mass reference range",
                },
                {
                    "check": "positive_fuel_rate",
                    "scenario": scenario,
                    "value": float(frame["fuel_flow_kgs"].min()),
                    "threshold": 0.0,
                    "passed": bool((frame["fuel_flow_kgs"] > 0).all()),
                    "notes": "fuel flow remains positive along path",
                },
                {
                    "check": "positive_atmosphere",
                    "scenario": scenario,
                    "value": float(min(frame["temperature_k"].min(), frame["density_kgm3"].min(), frame["sound_speed_mps"].min())),
                    "threshold": 0.0,
                    "passed": bool(
                        (frame["temperature_k"] > 0).all()
                        and (frame["density_kgm3"] > 0).all()
                        and (frame["sound_speed_mps"] > 0).all()
                    ),
                    "notes": "temperature, density, and sound speed remain physical",
                },
                {
                    "check": "implicit_denominator_positive",
                    "scenario": scenario,
                    "value": float(frame["implicit_denominator"].min()),
                    "threshold": 0.1,
                    "passed": bool((frame["implicit_denominator"] > 0.1).all()),
                    "notes": "implicit mass ODE denominator stays away from zero",
                },
                {
                    "check": "hydrostatic_residual",
                    "scenario": scenario,
                    "value": hydrostatic_residual,
                    "threshold": 1e-4,
                    "passed": bool(hydrostatic_residual < 1e-4),
                    "notes": "pressure profile satisfies dp/dh=-rho*g for the constant temperature offset model",
                },
                {
                    "check": "atmosphere_layer_valid",
                    "scenario": scenario,
                    "value": invalid_layer_count,
                    "threshold": 0,
                    "passed": bool(invalid_layer_count == 0 and frame["height_m"].max() <= 11_000.0),
                    "notes": "fixed q1 reference path stays in the troposphere and uses the matching layer formula",
                },
                {
                    "check": "terminal_mass_constraint",
                    "scenario": scenario,
                    "value": terminal_mass_margin,
                    "threshold": 0.0,
                    "passed": bool(terminal_mass_margin >= -1e-3),
                    "notes": "fixed ISA reference range keeps terminal mass at or above the problem lower bound",
                },
                {
                    "check": "time_path_integral_consistency",
                    "scenario": scenario,
                    "value": max_integral_error,
                    "threshold": 0.05,
                    "passed": bool(max_integral_error < 0.05),
                    "notes": "mass loss, time integral, and path integral agree",
                },
                {
                    "check": "small_angle",
                    "scenario": scenario,
                    "value": max_path_angle,
                    "threshold": 0.05,
                    "passed": bool(max_path_angle < 0.05),
                    "notes": "quasi-steady cruise-climb path angle remains small",
                },
                {
                    "check": "positive_thrust",
                    "scenario": scenario,
                    "value": thrust_positive_min,
                    "threshold": 0.0,
                    "passed": bool(thrust_positive_min > 0.0),
                    "notes": "required thrust remains positive along path",
                },
                {
                    "check": "path_derivative_smoothness",
                    "scenario": scenario,
                    "value": smoothness,
                    "threshold": 1e-4,
                    "passed": bool(smoothness < 1e-4),
                    "notes": "height-distance derivative has no numerical jumps",
                },
            ]
        )
    standard = float(summary.loc[summary["scenario"] == "standard_isa", "fuel_used_kg"].iloc[0])
    corrected = float(summary.loc[summary["scenario"] == "temp_plus_10K", "fuel_used_kg"].iloc[0])
    delta = corrected - standard
    rows.append(
        {
            "check": "temperature_correction_effect",
            "scenario": "temp_plus_10K",
            "value": delta,
            "threshold": 0.0,
            "passed": bool(abs(delta) > 1e-6),
            "notes": "hydrostatic non-standard atmosphere correction changes fixed-range fuel",
        }
    )
    zero_repeat = simulate_fixed_range(
        "standard_isa_repeat",
        params=params,
        temperature_offset_k=0.0,
        target_distance_m=target_distance_m,
    )
    standard_profile = profiles["standard_isa"]
    zero_error = abs(float(zero_repeat["mass_kg"].iloc[-1]) - float(standard_profile["mass_kg"].iloc[-1]))
    rows.append(
        {
            "check": "delta_zero_converges_to_isa",
            "scenario": "standard_isa",
            "value": zero_error,
            "threshold": 1e-6,
            "passed": bool(zero_error < 1e-6),
            "notes": "temperature-offset implementation returns to ISA at DeltaT=0",
        }
    )
    coarse_params = Q2Parameters(max_step_s=params.max_step_s * 2.0)
    coarse_terminal_profiles = [
        simulate_fixed_range(
            f"{temperature_scenario_name(offset)}_coarse_terminal",
            params=coarse_params,
            temperature_offset_k=offset,
            stop_at_terminal_mass=True,
        )
        for offset in coarse_params.temperature_offsets_k
    ]
    coarse_target_distance = min(float(profile["distance_m"].iloc[-1]) for profile in coarse_terminal_profiles)
    coarse = simulate_fixed_range(
        "standard_isa_coarse",
        params=coarse_params,
        temperature_offset_k=0.0,
        target_distance_m=coarse_target_distance,
    )
    step_delta_fuel = abs((params.m0_kg - coarse["mass_kg"].iloc[-1]) - standard)
    rows.append(
        {
            "check": "step_sensitivity",
            "scenario": "standard_isa",
            "value": step_delta_fuel,
            "threshold": 0.1,
            "passed": bool(step_delta_fuel < 0.1),
            "notes": "reported fuel is stable when max_step_s is doubled",
        }
    )
    minus = float(summary.loc[summary["scenario"] == temperature_scenario_name(-10.0), "fuel_delta_vs_standard_kg"].iloc[0])
    plus = float(summary.loc[summary["scenario"] == temperature_scenario_name(10.0), "fuel_delta_vs_standard_kg"].iloc[0])
    opposite_sign = minus * plus < 0.0
    rows.append(
        {
            "check": "positive_negative_temperature_response",
            "scenario": "temperature_sensitivity",
            "value": plus - minus,
            "threshold": 0.0,
            "passed": bool(opposite_sign),
            "notes": "negative and positive temperature offsets move fuel in opposite directions around ISA",
        }
    )
    return pd.DataFrame(rows)


def _max_hydrostatic_residual(frame: pd.DataFrame, offset_k: float, params: Q2Parameters) -> float:
    heights = frame["height_m"].to_numpy(dtype=float)
    if len(heights) == 0:
        return float("inf")
    sample = np.linspace(float(heights.min()), float(heights.max()), num=min(25, max(len(heights), 2)))
    residuals = []
    dh = 0.1
    for height in sample:
        _, rho_mid, _, _ = atmosphere(float(height), temperature_offset_k=offset_k)
        _, _, _, p_low = atmosphere(float(height - dh), temperature_offset_k=offset_k)
        _, _, _, p_high = atmosphere(float(height + dh), temperature_offset_k=offset_k)
        dp_dh = (p_high - p_low) / (2.0 * dh)
        residuals.append(abs(dp_dh + rho_mid * params.g_mps2) / (rho_mid * params.g_mps2))
    return float(max(residuals))


def run_validation(config_path: str | None = None, root: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    del config_path
    root = root or ROOT
    validation = validation_summary(root)
    qdir = root / "questions" / "q2"
    save_table(validation, stem="validation_summary", question_dir=qdir)
    return validation, pd.DataFrame()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate q2 outputs")
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args()
    validation, _ = run_validation(args.config, ROOT)
    failed = validation[~validation["passed"]]
    if not failed.empty:
        print(failed.to_string(index=False))
        return 1
    print("q2 validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
