#!/usr/bin/env python3
"""Validation and sensitivity analysis for q1."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
import math

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [SRC, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from modeling_common.artifacts import save_table  # noqa: E402
from aircraft_model import (  # noqa: E402
    AircraftParameters,
    drag_n,
    fuel_penalty,
    lift_coefficient,
    load_parameters,
    validate_parameters,
)
from atmosphere import density_kgm3, sound_speed_mps, wind_speed_mps  # noqa: E402
from simulate import comparison_table, run_strategies  # noqa: E402
import strategy_constant_mach as mach_strategy  # noqa: E402
import strategy_constant_speed as speed_strategy  # noqa: E402


def _profiles(root: Path) -> dict[str, pd.DataFrame]:
    data_dir = root / "artifacts" / "q1" / "data"
    return {
        "constant_speed": pd.read_csv(data_dir / "constant_speed_profile.csv"),
        "constant_mach": pd.read_csv(data_dir / "constant_mach_profile.csv"),
    }


def _implicit_denominator(mass_kg: float, airspeed_mps: float, dh_dm: float, d_v_dm: float, params: AircraftParameters) -> float:
    a_term = mass_kg * d_v_dm + (mass_kg * params.g_mps2 / airspeed_mps) * dh_dm
    return 1.0 + params.c_t_kg_per_ns * fuel_penalty(airspeed_mps, params) * a_term


def validation_summary(root: Path | None = None, params: AircraftParameters | None = None) -> pd.DataFrame:
    root = root or ROOT
    params = params or AircraftParameters()
    validate_parameters(params)
    profiles = _profiles(root)
    rows: list[dict[str, object]] = []

    for strategy, frame in profiles.items():
        max_gamma_deg = float(
            (frame["climb_rate_mps"].abs() / frame["airspeed_mps"]).clip(upper=1.0).map(math.asin).max()
            * 180.0
            / math.pi
        )
        derivative_fn = speed_strategy.derivatives_wrt_mass if strategy == "constant_speed" else mach_strategy.derivatives_wrt_mass
        denominators = [
            _implicit_denominator(
                float(row.mass_kg),
                float(row.airspeed_mps),
                *derivative_fn(float(row.mass_kg), params),
                params,
            )
            for row in frame.itertuples(index=False)
        ]
        min_denominator = float(min(denominators))
        min_thrust = float(frame["thrust_N"].min())
        rows.extend(
            [
                {
                    "check": "initial_conditions",
                    "strategy": strategy,
                    "value": abs(frame["mass_kg"].iloc[0] - params.m0_kg)
                    + abs(frame["height_m"].iloc[0] - params.h0_m),
                    "threshold": 1e-6,
                    "passed": bool(
                        abs(frame["mass_kg"].iloc[0] - params.m0_kg) < 1e-6
                        and abs(frame["height_m"].iloc[0] - params.h0_m) < 1e-6
                    ),
                    "notes": "initial mass and height match题设",
                },
                {
                    "check": "mass_monotonic",
                    "strategy": strategy,
                    "value": float((frame["mass_kg"].diff().fillna(0) <= 1e-9).all()),
                    "threshold": 1.0,
                    "passed": bool(frame["mass_kg"].is_monotonic_decreasing),
                    "notes": "mass must not increase",
                },
                {
                    "check": "lift_balance_residual",
                    "strategy": strategy,
                    "value": frame["lift_balance_residual"].abs().max(),
                    "threshold": 1e-6,
                    "passed": bool(frame["lift_balance_residual"].abs().max() < 1e-6),
                    "notes": "dimensionless residual",
                },
                {
                    "check": "energy_residual",
                    "strategy": strategy,
                    "value": frame["energy_residual"].abs().max(),
                    "threshold": 1e-6,
                    "passed": bool(frame["energy_residual"].abs().max() < 1e-6),
                    "notes": "dimensionless residual",
                },
                {
                    "check": "positive_atmosphere_and_speed",
                    "strategy": strategy,
                    "value": min(
                        frame["density_kgm3"].min(),
                        frame["airspeed_mps"].min(),
                        frame["groundspeed_mps"].min(),
                    ),
                    "threshold": 0.0,
                    "passed": bool(
                        (frame["density_kgm3"] > 0).all()
                        and (frame["airspeed_mps"] > 0).all()
                        and (frame["groundspeed_mps"] > 0).all()
                    ),
                    "notes": "density, airspeed, and groundspeed are physical",
                },
                {
                    "check": "small_angle_valid",
                    "strategy": strategy,
                    "value": max_gamma_deg,
                    "threshold": 1.0,
                    "passed": bool(max_gamma_deg < 1.0),
                    "notes": "maximum flight-path angle in degrees",
                },
                {
                    "check": "implicit_denominator_positive",
                    "strategy": strategy,
                    "value": min_denominator,
                    "threshold": 0.1,
                    "passed": bool(min_denominator > 0.1),
                    "notes": "minimum denominator of implicit mass ODE",
                },
                {
                    "check": "thrust_positive",
                    "strategy": strategy,
                    "value": min_thrust,
                    "threshold": 0.0,
                    "passed": bool(min_thrust > 0.0),
                    "notes": "minimum thrust along trajectory",
                },
            ]
        )
        if strategy == "constant_speed":
            analytic_height = params.h0_m - 7300.0 * math.log(params.mf_kg / params.m0_kg)
            error = abs(float(frame["height_m"].iloc[-1]) - analytic_height)
            rows.append(
                {
                    "check": "analytic_height_match",
                    "strategy": strategy,
                    "value": error,
                    "threshold": 1.0e-6,
                    "passed": bool(error < 1.0e-6),
                    "notes": "constant-speed terminal height matches analytic expression",
                }
            )
        if strategy == "constant_mach":
            mach_range = float(frame["mach"].max() - frame["mach"].min())
            rows.append(
                {
                    "check": "mach_constraint_valid",
                    "strategy": strategy,
                    "value": mach_range,
                    "threshold": 1.0e-9,
                    "passed": bool(mach_range < 1.0e-9),
                    "notes": "constant-Mach trajectory keeps Mach number fixed",
                }
            )

    outputs_default = run_strategies(params)
    default_comparison = comparison_table(outputs_default, params).set_index("strategy")
    coarse_params = replace(params, max_step_s=params.max_step_s * 2.0)
    fine_params = replace(params, max_step_s=max(params.max_step_s / 2.0, 0.5))
    coarse_comparison = comparison_table(run_strategies(coarse_params), coarse_params).set_index("strategy")
    fine_comparison = comparison_table(run_strategies(fine_params), fine_params).set_index("strategy")
    for strategy in outputs_default:
        metric_specs = [
            ("final_time_s", 0.5, "s"),
            ("final_distance_m", 150.0, "m"),
            ("mean_climb_rate_mps", 1.0e-3, "m/s"),
        ]
        for metric, threshold, unit in metric_specs:
            default_value = float(default_comparison.loc[strategy, metric])
            coarse_delta = abs(float(coarse_comparison.loc[strategy, metric]) - default_value)
            fine_delta = abs(float(fine_comparison.loc[strategy, metric]) - default_value)
            max_delta = max(coarse_delta, fine_delta)
            rows.append(
                {
                    "check": f"step_sensitivity_{metric.removesuffix('_s').removesuffix('_m').removesuffix('_mps')}",
                    "strategy": strategy,
                    "value": max_delta,
                    "threshold": threshold,
                    "passed": bool(max_delta < threshold),
                    "notes": f"max-step half/double {metric} difference ({unit})",
                }
            )

    baseline_outputs = run_strategies(params)
    no_wind_rows = []
    for strategy, frame in baseline_outputs.items():
        no_wind_distance = (frame["distance_m"].iloc[-1] - frame["time_s"].diff().fillna(0).mul(frame["groundspeed_mps"] - frame["airspeed_mps"]).sum())
        no_wind_rows.append((strategy, frame["distance_m"].iloc[-1] - no_wind_distance))
    for strategy, wind_gain in no_wind_rows:
        rows.append(
            {
                "check": "wind_effect_distance",
                "strategy": strategy,
                "value": wind_gain,
                "threshold": 0.0,
                "passed": bool(wind_gain > 0),
                "notes": "confirmed positive tailwind increases ground distance",
            }
        )

    for height_m, speed_mps in [(0.0, 180.0), (16_000.0, 280.0)]:
        rho = density_kgm3(height_m)
        sound = sound_speed_mps(height_m)
        cl = lift_coefficient(height_m, speed_mps, params.mf_kg, params)
        drag = drag_n(height_m, speed_mps, params.mf_kg, params)
        rows.append(
            {
                "check": "extreme_state_physical",
                "strategy": f"h={height_m:g},V={speed_mps:g}",
                "value": min(rho, sound, cl, drag, wind_speed_mps(height_m)),
                "threshold": 0.0,
                "passed": bool(rho > 0 and sound > 0 and cl > 0 and drag > 0),
                "notes": "extreme state retains physical atmosphere/aero values",
            }
        )

    return pd.DataFrame(rows)


def _configured_relative_changes(config_path: str | None) -> list[float]:
    if not config_path:
        return [-0.20, -0.10, 0.10, 0.20]
    with open(config_path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    changes = config.get("validation", {}).get("sensitivity_relative_changes", [-0.20, -0.10, 0.10, 0.20])
    if not changes:
        raise ValueError("validation.sensitivity_relative_changes must not be empty")
    return [float(change) for change in changes]


def _change_label(change: float) -> str:
    pct = abs(int(round(change * 100)))
    direction = "plus" if change > 0 else "minus"
    return f"beta_{direction}_{pct}pct"


def sensitivity_summary(params: AircraftParameters | None = None, config_path: str | None = None) -> pd.DataFrame:
    params = params or AircraftParameters()
    rows: list[dict[str, float | str]] = []
    scenarios = [
        ("ct_engineering_check", replace(params, c_t_kg_per_ns=2.8e-5)),
    ]
    scenarios.extend(
        (_change_label(change), replace(params, beta_s2pm2=params.beta_s2pm2 * (1.0 + change)))
        for change in _configured_relative_changes(config_path)
    )
    for scenario, scenario_params in scenarios:
        outputs = run_strategies(scenario_params)
        comparison = comparison_table(outputs, scenario_params)
        for row in comparison.to_dict(orient="records"):
            rows.append(
                {
                    "scenario": scenario,
                    "strategy": row["strategy"],
                    "final_time_s": row["final_time_s"],
                    "final_distance_m": row["final_distance_m"],
                    "final_height_m": row["final_height_m"],
                    "mean_climb_rate_mps": row["mean_climb_rate_mps"],
                }
            )
    return pd.DataFrame(rows)


def run_validation(config_path: str | None = None, root: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = root or ROOT
    params = load_parameters(config_path)
    qdir = root / "questions" / "q1"
    validation = validation_summary(root, params)
    sensitivity = sensitivity_summary(params, config_path)
    save_table(validation, stem="validation_summary", question_dir=qdir)
    save_table(sensitivity, stem="sensitivity_summary", question_dir=qdir)
    return validation, sensitivity


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate q1 outputs")
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args()
    validation, _ = run_validation(args.config, ROOT)
    failed = validation[~validation["passed"]]
    if not failed.empty:
        print(failed.to_string(index=False))
        return 1
    print("q1 validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
