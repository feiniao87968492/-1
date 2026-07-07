#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
Q2_SCRIPTS = ROOT / "questions" / "q2" / "scripts"
Q3_SCRIPTS = ROOT / "questions" / "q3" / "scripts"
for path in [SRC, Q2_SCRIPTS, Q3_SCRIPTS]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fuel_path_model import Q2Parameters  # noqa: E402
from fuel_path_model import atmosphere as layered_atmosphere  # noqa: E402
from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402
from smooth_atmosphere import atmosphere, max_deviation_from_layered_isa, smoothing_diagnostics_table  # noqa: E402
from solve_feasibility_no_wind import Q3Config, load_q3_config  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q3 no-wind range-domain collocation feasibility gate")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--nodes", type=int, default=31)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="project the Gate 1 trajectory into the Gate 2 model without optimizing",
    )
    return parser.parse_args()


def _load_gate_config(root: Path, config_path: str) -> dict:
    with (root / config_path).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config["q3_optimal_control"]["feasibility_gate"]


def _gate1_trajectory(root: Path) -> pd.DataFrame:
    path = root / "questions" / "q3" / "artifacts" / "tables" / "no_wind_feasibility_trajectory.csv"
    if not path.exists():
        raise FileNotFoundError("Run questions/q3/scripts/solve_feasibility_no_wind.py before Gate 2 dry-run")
    frame = pd.read_csv(path).sort_values("distance_m").drop_duplicates("distance_m")
    required = {"distance_m", "height_m", "airspeed_mps", "thrust_n", "gamma_rad"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Gate 1 trajectory missing columns: {sorted(missing)}")
    return frame


def _interp(frame: pd.DataFrame, column: str, distance: np.ndarray) -> np.ndarray:
    return np.interp(distance, frame["distance_m"].to_numpy(dtype=float), frame[column].to_numpy(dtype=float))


def _rates(
    *,
    height_m: float,
    airspeed_mps: float,
    mass_kg: float,
    thrust_n: float,
    gamma_rad: float,
    params: Q2Parameters,
    atmosphere_model=atmosphere,
) -> dict[str, float]:
    temperature_k, density_kgm3, sound_speed_mps, pressure_pa = atmosphere_model(height_m)
    cl = (
        2.0
        * mass_kg
        * params.g_mps2
        * math.cos(gamma_rad)
        / (density_kgm3 * airspeed_mps**2 * params.wing_area_m2)
    )
    cd = params.cd0 + params.induced_k * cl**2
    drag_n = 0.5 * density_kgm3 * airspeed_mps**2 * params.wing_area_m2 * cd
    ground_speed_mps = airspeed_mps * math.cos(gamma_rad)
    if ground_speed_mps <= 0.0:
        raise ValueError("non-positive range-domain denominator")
    fuel_penalty = 1.0 + params.beta_s2pm2 * (airspeed_mps - params.v_opt_mps) ** 2
    return {
        "temperature_k": temperature_k,
        "density_kgm3": density_kgm3,
        "sound_speed_mps": sound_speed_mps,
        "pressure_pa": pressure_pa,
        "groundspeed_mps": ground_speed_mps,
        "mach": airspeed_mps / sound_speed_mps,
        "cl": cl,
        "cd": cd,
        "drag_n": drag_n,
        "dh_dx": airspeed_mps * math.sin(gamma_rad) / ground_speed_mps,
        "dV_dx": ((thrust_n - drag_n) / mass_kg - params.g_mps2 * math.sin(gamma_rad)) / ground_speed_mps,
        "dm_dx": -params.c_t_kg_per_ns * thrust_n * fuel_penalty / ground_speed_mps,
        "dt_dx": 1.0 / ground_speed_mps,
    }


def _project_gate1_warm_start(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    atmosphere_model=atmosphere,
) -> pd.DataFrame:
    distance = np.linspace(0.0, q3.target_distance_m, nodes)
    height = _interp(gate1, "height_m", distance)
    airspeed = _interp(gate1, "airspeed_mps", distance)
    thrust = _interp(gate1, "thrust_n", distance)
    gamma = _interp(gate1, "gamma_rad", distance)
    height[0] = 9500.0
    airspeed[0] = q3.terminal_airspeed_mps
    height[-1] = q3.terminal_height_m
    airspeed[-1] = q3.terminal_airspeed_mps

    mass = np.zeros(nodes)
    time = np.zeros(nodes)
    mass[0] = params.m0_kg
    records: list[dict[str, float]] = []

    for index in range(nodes):
        rates = _rates(
            height_m=float(height[index]),
            airspeed_mps=float(airspeed[index]),
            mass_kg=float(mass[index]) if index == 0 else float(mass[index]),
            thrust_n=float(thrust[index]),
            gamma_rad=float(gamma[index]),
            params=params,
            atmosphere_model=atmosphere_model,
        )
        records.append(
            {
                "distance_m": float(distance[index]),
                "height_m": float(height[index]),
                "airspeed_mps": float(airspeed[index]),
                "mass_kg": float(mass[index]),
                "time_s": float(time[index]),
                "thrust_n": float(thrust[index]),
                "gamma_rad": float(gamma[index]),
                **rates,
            }
        )
        if index == nodes - 1:
            break
        dx = distance[index + 1] - distance[index]
        rates_next_guess = _rates(
            height_m=float(height[index + 1]),
            airspeed_mps=float(airspeed[index + 1]),
            mass_kg=float(mass[index]),
            thrust_n=float(thrust[index + 1]),
            gamma_rad=float(gamma[index + 1]),
            params=params,
            atmosphere_model=atmosphere_model,
        )
        mass[index + 1] = mass[index] + 0.5 * dx * (rates["dm_dx"] + rates_next_guess["dm_dx"])
        time[index + 1] = time[index] + 0.5 * dx * (rates["dt_dx"] + rates_next_guess["dt_dx"])
    frame = pd.DataFrame.from_records(records)
    frame["mass_kg"] = mass
    frame["time_s"] = time
    return frame


def _scaled_constraint_violation(row: pd.Series, q3: Q3Config) -> float:
    height_scale = 10_000.0
    speed_scale = 240.0
    thrust_scale = max(q3.thrust_max_n, 1.0)
    gamma_scale = max(q3.gamma_max_rad, 1.0e-9)
    return max(
        0.0,
        (q3.h_min_m - row["height_m"]) / height_scale,
        (row["height_m"] - q3.h_max_m) / height_scale,
        (q3.v_min_mps - row["airspeed_mps"]) / speed_scale,
        (row["airspeed_mps"] - q3.v_max_mps) / speed_scale,
        (q3.thrust_min_n - row["thrust_n"]) / thrust_scale,
        (row["thrust_n"] - q3.thrust_max_n) / thrust_scale,
        (abs(row["gamma_rad"]) - q3.gamma_max_rad) / gamma_scale,
        row["mach"] - q3.mach_max,
    )


def _collocation_diagnostics(trajectory: pd.DataFrame, q3: Q3Config) -> dict[str, float]:
    x = trajectory["distance_m"].to_numpy(dtype=float)
    h = trajectory["height_m"].to_numpy(dtype=float)
    v = trajectory["airspeed_mps"].to_numpy(dtype=float)
    m = trajectory["mass_kg"].to_numpy(dtype=float)
    t = trajectory["time_s"].to_numpy(dtype=float)
    rates = trajectory[["dh_dx", "dV_dx", "dm_dx", "dt_dx"]].to_numpy(dtype=float)
    defect_max = 0.0
    for index in range(len(x) - 1):
        dx = x[index + 1] - x[index]
        defects = np.array(
            [
                h[index + 1] - h[index] - 0.5 * dx * (rates[index, 0] + rates[index + 1, 0]),
                v[index + 1] - v[index] - 0.5 * dx * (rates[index, 1] + rates[index + 1, 1]),
                m[index + 1] - m[index] - 0.5 * dx * (rates[index, 2] + rates[index + 1, 2]),
                t[index + 1] - t[index] - 0.5 * dx * (rates[index, 3] + rates[index + 1, 3]),
            ]
        )
        scaled = np.array([defects[0] / 10_000.0, defects[1] / 240.0, defects[2] / 72_450.0, defects[3] / 800.0])
        defect_max = max(defect_max, float(np.max(np.abs(scaled))))
    midpoint_height = 0.5 * (h[:-1] + h[1:])
    midpoint_violation = np.maximum(0.0, midpoint_height - q3.h_max_m)
    return {
        "scaled_collocation_defect_inf": defect_max,
        "max_midpoint_height_violation_m": float(np.max(midpoint_violation)) if len(midpoint_violation) else 0.0,
    }


def _hmax_sensitivity(trajectory: pd.DataFrame, hmax_values: list[float], q3: Q3Config) -> pd.DataFrame:
    rows = []
    for hmax in hmax_values:
        max_height = float(trajectory["height_m"].max())
        final_mass = float(trajectory["mass_kg"].iloc[-1])
        rows.append(
            {
                "h_max_m": hmax,
                "warm_start_max_height_m": max_height,
                "warm_start_height_violation_m": max(0.0, max_height - hmax),
                "warm_start_terminal_mass_shortfall_kg": max(0.0, q3.terminal_mass_min_kg - final_mass),
                "status": "warm_start_only_not_optimized",
            }
        )
    return pd.DataFrame(rows)


def _projection_audit(
    *,
    gate1: pd.DataFrame,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    c1_trajectory: pd.DataFrame,
) -> pd.DataFrame:
    original_final_mass = float(gate1["mass_kg"].iloc[-1]) if "mass_kg" in gate1.columns else float("nan")
    original_final_time = float(gate1["time_s"].iloc[-1]) if "time_s" in gate1.columns else float("nan")
    original_final_height = float(gate1["height_m"].iloc[-1])
    original_final_speed = float(gate1["airspeed_mps"].iloc[-1])

    layered_projection = _project_gate1_warm_start(
        gate1,
        q3=q3,
        params=params,
        nodes=nodes,
        atmosphere_model=layered_atmosphere,
    )
    layered_final = layered_projection.iloc[-1]
    c1_final = c1_trajectory.iloc[-1]
    rows = [
        {
            "scenario": "A_gate1_original",
            "atmosphere": "layered_isa",
            "control_trajectory": "gate1_original",
            "integration_grid": "gate1_original",
            "nodes": int(len(gate1)),
            "terminal_mass_kg": original_final_mass,
            "terminal_mass_shortfall_kg": max(0.0, q3.terminal_mass_min_kg - original_final_mass),
            "final_time_s": original_final_time,
            "terminal_height_m": original_final_height,
            "terminal_airspeed_mps": original_final_speed,
            "mass_difference_from_previous_kg": 0.0,
        },
        {
            "scenario": "B_gate1_interpolated_gate2_grid_original_atmosphere",
            "atmosphere": "layered_isa",
            "control_trajectory": "gate1_interpolated",
            "integration_grid": "gate2_uniform_grid",
            "nodes": nodes,
            "terminal_mass_kg": float(layered_final["mass_kg"]),
            "terminal_mass_shortfall_kg": max(0.0, q3.terminal_mass_min_kg - float(layered_final["mass_kg"])),
            "final_time_s": float(layered_final["time_s"]),
            "terminal_height_m": float(layered_final["height_m"]),
            "terminal_airspeed_mps": float(layered_final["airspeed_mps"]),
            "mass_difference_from_previous_kg": original_final_mass - float(layered_final["mass_kg"]),
        },
        {
            "scenario": "C_gate1_interpolated_gate2_grid_c1_atmosphere",
            "atmosphere": "C1_temperature_hydrostatic_pressure",
            "control_trajectory": "gate1_interpolated",
            "integration_grid": "gate2_uniform_grid",
            "nodes": nodes,
            "terminal_mass_kg": float(c1_final["mass_kg"]),
            "terminal_mass_shortfall_kg": max(0.0, q3.terminal_mass_min_kg - float(c1_final["mass_kg"])),
            "final_time_s": float(c1_final["time_s"]),
            "terminal_height_m": float(c1_final["height_m"]),
            "terminal_airspeed_mps": float(c1_final["airspeed_mps"]),
            "mass_difference_from_previous_kg": float(layered_final["mass_kg"]) - float(c1_final["mass_kg"]),
        },
    ]
    return pd.DataFrame(rows)


def _atmosphere_coupling_diagnostics(params: Q2Parameters) -> pd.DataFrame:
    state = {
        "height_m": 11_000.0,
        "airspeed_mps": 235.0,
        "mass_kg": 67_000.0,
        "thrust_n": 50_000.0,
        "gamma_rad": 0.0,
    }
    layered = _rates(**state, params=params, atmosphere_model=layered_atmosphere)
    c1 = _rates(**state, params=params, atmosphere_model=atmosphere)
    desired_dv_dx = 5.0e-4
    fuel_penalty = 1.0 + params.beta_s2pm2 * (state["airspeed_mps"] - params.v_opt_mps) ** 2

    def required_thrust_row(rates: dict[str, float]) -> tuple[float, float]:
        required_thrust = rates["drag_n"] + state["mass_kg"] * (
            params.g_mps2 * math.sin(state["gamma_rad"]) + rates["groundspeed_mps"] * desired_dv_dx
        )
        dm_dx = -params.c_t_kg_per_ns * required_thrust * fuel_penalty / rates["groundspeed_mps"]
        return required_thrust, dm_dx

    layered_required_thrust, layered_required_dm_dx = required_thrust_row(layered)
    c1_required_thrust, c1_required_dm_dx = required_thrust_row(c1)
    return pd.DataFrame(
        [
            {
                **state,
                "required_dV_dx_per_m": desired_dv_dx,
                "layer_density_kgm3": layered["density_kgm3"],
                "c1_density_kgm3": c1["density_kgm3"],
                "density_delta_c1_minus_layer_kgm3": c1["density_kgm3"] - layered["density_kgm3"],
                "layer_drag_n": layered["drag_n"],
                "c1_drag_n": c1["drag_n"],
                "drag_delta_c1_minus_layer_n": c1["drag_n"] - layered["drag_n"],
                "layer_dV_dx_per_m": layered["dV_dx"],
                "c1_dV_dx_per_m": c1["dV_dx"],
                "dV_dx_delta_c1_minus_layer_per_m": c1["dV_dx"] - layered["dV_dx"],
                "layer_dm_dx_kgpm": layered["dm_dx"],
                "c1_dm_dx_kgpm": c1["dm_dx"],
                "dm_dx_delta_c1_minus_layer_kgpm": c1["dm_dx"] - layered["dm_dx"],
                "layer_required_thrust_n": layered_required_thrust,
                "c1_required_thrust_n": c1_required_thrust,
                "required_thrust_delta_c1_minus_layer_n": c1_required_thrust - layered_required_thrust,
                "layer_required_thrust_dm_dx_kgpm": layered_required_dm_dx,
                "c1_required_thrust_dm_dx_kgpm": c1_required_dm_dx,
                "required_thrust_dm_dx_delta_c1_minus_layer_kgpm": c1_required_dm_dx - layered_required_dm_dx,
                "interpretation": "fixed_thrust_mass_rate_is_density_independent_required_thrust_mass_rate_is_not",
            }
        ]
    )


def main() -> int:
    args = parse_args()
    if args.nodes < 5:
        raise ValueError("--nodes must be at least 5")
    if not args.dry_run:
        raise NotImplementedError("Gate 2 optimizer is not enabled yet; run with --dry-run for readiness projection")

    root = project_root()
    q3 = load_q3_config(root, args.config)
    gate_config = _load_gate_config(root, args.config)
    params = Q2Parameters(terminal_mass_kg=q3.terminal_mass_min_kg)
    gate1 = _gate1_trajectory(root)
    trajectory = _project_gate1_warm_start(gate1, q3=q3, params=params, nodes=args.nodes)
    trajectory["scaled_constraint_violation"] = trajectory.apply(_scaled_constraint_violation, axis=1, q3=q3)

    diagnostics = _collocation_diagnostics(trajectory, q3)
    atmosphere_deviation = max_deviation_from_layered_isa()
    final = trajectory.iloc[-1]
    summary = pd.DataFrame(
        [
            {
                "wind_model": "no_wind",
                "method": "range_domain_collocation_readiness_dry_run",
                "nodes": args.nodes,
                "solver_status": "dry_run_not_optimized",
                "atmosphere_model": "C1_temperature_hydrostatic_pressure",
                "terminal_mass_kg": float(final["mass_kg"]),
                "terminal_mass_shortfall_kg": max(0.0, q3.terminal_mass_min_kg - float(final["mass_kg"])),
                "terminal_height_error_m": float(final["height_m"] - q3.terminal_height_m),
                "terminal_speed_error_mps": float(final["airspeed_mps"] - q3.terminal_airspeed_mps),
                "final_time_s": float(final["time_s"]),
                "max_scaled_constraint_violation": float(trajectory["scaled_constraint_violation"].max()),
                "constraint_violation_scale": "nondimensional",
                **diagnostics,
                **atmosphere_deviation,
                "slack_smoothing_tolerance_kg": float(gate_config["slack_smoothing_tolerance_kg"]),
            }
        ]
    )

    qdir = root / "questions" / "q3"
    save_table(summary, stem="no_wind_collocation_gate", question_dir=qdir)
    save_table(trajectory, stem="no_wind_collocation_trajectory", question_dir=qdir)
    hmax_diagnostic = _hmax_sensitivity(trajectory, [float(x) for x in gate_config["hmax_sensitivity_m"]], q3)
    save_table(hmax_diagnostic, stem="warm_start_hmax_diagnostic", question_dir=qdir)
    save_table(hmax_diagnostic, stem="no_wind_hmax_sensitivity", question_dir=qdir)
    save_table(
        smoothing_diagnostics_table(),
        stem="atmosphere_smoothing_diagnostics",
        question_dir=qdir,
    )
    save_table(
        _projection_audit(gate1=gate1, q3=q3, params=params, nodes=args.nodes, c1_trajectory=trajectory),
        stem="gate1_to_collocation_projection_audit",
        question_dir=qdir,
    )
    save_table(
        _atmosphere_coupling_diagnostics(params),
        stem="atmosphere_coupling_diagnostics",
        question_dir=qdir,
    )
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
