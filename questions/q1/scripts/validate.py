#!/usr/bin/env python3
"""Validation and sensitivity analysis for q1."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [SRC, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from modeling_common.artifacts import save_table  # noqa: E402
from aircraft_model import AircraftParameters, drag_n, lift_coefficient, load_parameters, validate_parameters  # noqa: E402
from atmosphere import density_kgm3, sound_speed_mps, wind_speed_mps  # noqa: E402
from simulate import comparison_table, run_strategies  # noqa: E402


def _profiles(root: Path) -> dict[str, pd.DataFrame]:
    data_dir = root / "artifacts" / "q1" / "data"
    return {
        "constant_speed": pd.read_csv(data_dir / "constant_speed_profile.csv"),
        "constant_mach": pd.read_csv(data_dir / "constant_mach_profile.csv"),
    }


def validation_summary(root: Path | None = None, params: AircraftParameters | None = None) -> pd.DataFrame:
    root = root or ROOT
    params = params or AircraftParameters()
    validate_parameters(params)
    profiles = _profiles(root)
    rows: list[dict[str, object]] = []

    for strategy, frame in profiles.items():
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
            ]
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
