#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.integrate import solve_ivp
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
Q2_SCRIPTS = ROOT / "questions" / "q2" / "scripts"
for path in [SRC, Q2_SCRIPTS]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fuel_path_model import Q2Parameters, ReferencePath, atmosphere, load_reference_path  # noqa: E402
from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402


@dataclass(frozen=True)
class Q3Config:
    target_distance_m: float
    terminal_height_m: float
    terminal_airspeed_mps: float
    h_min_m: float
    h_max_m: float
    v_min_mps: float
    v_max_mps: float
    mach_max: float
    thrust_min_n: float
    thrust_max_n: float
    gamma_max_rad: float
    terminal_mass_min_kg: float


@dataclass(frozen=True)
class PathEvaluation:
    trajectory: pd.DataFrame
    final_mass_kg: float
    final_time_s: float
    terminal_mass_slack_kg: float
    max_constraint_violation: float
    max_abs_path_residual: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q3 no-wind feasibility gate")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--nodes", type=int, default=31)
    return parser.parse_args()


def load_q3_config(root: Path, config_path: str) -> Q3Config:
    with (root / config_path).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    q3 = config.get("q3_optimal_control")
    if not isinstance(q3, dict):
        raise ValueError("configs/default.yaml missing q3_optimal_control")
    bounds = q3.get("bounds", {})
    return Q3Config(
        target_distance_m=float(q3["fixed_range_m"]),
        terminal_height_m=float(q3["terminal_height_m"]),
        terminal_airspeed_mps=float(q3["terminal_airspeed_mps"]),
        h_min_m=float(bounds["h_min_m"]),
        h_max_m=float(bounds["h_max_m"]),
        v_min_mps=float(bounds["v_min_mps"]),
        v_max_mps=float(bounds["v_max_mps"]),
        mach_max=float(bounds["mach_max"]),
        thrust_min_n=float(bounds["thrust_min_n"]),
        thrust_max_n=float(bounds["thrust_max_n"]),
        gamma_max_rad=float(bounds["gamma_max_rad"]),
        terminal_mass_min_kg=float(bounds["mass_min_kg"]),
    )


def _reference_height(distance_m: np.ndarray, reference_path: ReferencePath) -> np.ndarray:
    return np.interp(distance_m, reference_path.distance_m, reference_path.height_m)


def _reference_dh_dx(distance_m: np.ndarray, reference_path: ReferencePath) -> np.ndarray:
    return np.interp(distance_m, reference_path.distance_m, reference_path.dh_dx)


def _profile(
    distance_m: np.ndarray,
    variables: np.ndarray,
    *,
    reference_path: ReferencePath,
    q3: Q3Config,
) -> dict[str, np.ndarray]:
    target = q3.target_distance_m
    sigma = distance_m / target
    h1, h2, v1, v2 = variables
    reference_start = float(np.interp(0.0, reference_path.distance_m, reference_path.height_m))
    reference_end = float(np.interp(target, reference_path.distance_m, reference_path.height_m))
    initial_height_m = 9500.0
    start_delta = initial_height_m - reference_start
    end_delta = q3.terminal_height_m - reference_end
    height = _reference_height(distance_m, reference_path)
    dh_dx = _reference_dh_dx(distance_m, reference_path)
    height = height + (1.0 - sigma) * start_delta + sigma * end_delta
    dh_dx = dh_dx + (end_delta - start_delta) / target
    height = height + h1 * np.sin(math.pi * sigma) + h2 * np.sin(2.0 * math.pi * sigma)
    dh_dx = dh_dx + h1 * math.pi / target * np.cos(math.pi * sigma)
    dh_dx = dh_dx + h2 * 2.0 * math.pi / target * np.cos(2.0 * math.pi * sigma)
    airspeed = q3.terminal_airspeed_mps
    airspeed = airspeed + v1 * np.sin(math.pi * sigma) + v2 * np.sin(2.0 * math.pi * sigma)
    dV_dx = v1 * math.pi / target * np.cos(math.pi * sigma)
    dV_dx = dV_dx + v2 * 2.0 * math.pi / target * np.cos(2.0 * math.pi * sigma)
    return {
        "height_m": height,
        "dh_dx": dh_dx,
        "airspeed_mps": airspeed,
        "dV_dx": dV_dx,
    }


def _rates_at(
    *,
    mass_kg: float,
    height_m: float,
    dh_dx: float,
    airspeed_mps: float,
    dV_dx: float,
    params: Q2Parameters,
    q3: Q3Config,
) -> dict[str, float]:
    gamma_rad = math.atan(dh_dx)
    temperature_k, density_kgm3, sound_speed_mps, _pressure_pa = atmosphere(height_m)
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
        raise ValueError("non-positive no-wind ground speed")
    thrust_n = mass_kg * (ground_speed_mps * dV_dx + params.g_mps2 * math.sin(gamma_rad)) + drag_n
    fuel_penalty = 1.0 + params.beta_s2pm2 * (airspeed_mps - params.v_opt_mps) ** 2
    fuel_per_meter_kgpm = params.c_t_kg_per_ns * thrust_n * fuel_penalty / ground_speed_mps
    mach = airspeed_mps / sound_speed_mps
    path_h_residual = dh_dx - airspeed_mps * math.sin(gamma_rad) / ground_speed_mps
    path_v_residual = dV_dx - ((thrust_n - drag_n) / mass_kg - params.g_mps2 * math.sin(gamma_rad)) / ground_speed_mps
    violation = max(
        q3.h_min_m - height_m,
        height_m - q3.h_max_m,
        q3.v_min_mps - airspeed_mps,
        airspeed_mps - q3.v_max_mps,
        mach - q3.mach_max,
        q3.thrust_min_n - thrust_n,
        thrust_n - q3.thrust_max_n,
        abs(gamma_rad) - q3.gamma_max_rad,
        0.0,
    )
    return {
        "temperature_k": temperature_k,
        "density_kgm3": density_kgm3,
        "airspeed_mps": airspeed_mps,
        "groundspeed_mps": ground_speed_mps,
        "gamma_rad": gamma_rad,
        "mach": mach,
        "cl": cl,
        "cd": cd,
        "drag_n": drag_n,
        "thrust_n": thrust_n,
        "fuel_per_meter_kgpm": fuel_per_meter_kgpm,
        "dm_dx": -fuel_per_meter_kgpm,
        "dt_dx": 1.0 / ground_speed_mps,
        "constraint_violation": violation,
        "path_residual": max(abs(path_h_residual), abs(path_v_residual)),
    }


def evaluate_path(
    variables: np.ndarray,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    reference_path: ReferencePath,
    nodes: int,
) -> PathEvaluation:
    distance_nodes = np.linspace(0.0, q3.target_distance_m, nodes)

    def rhs(distance_m: float, state: np.ndarray) -> list[float]:
        profile = _profile(np.array([distance_m]), variables, reference_path=reference_path, q3=q3)
        rates = _rates_at(
            mass_kg=float(state[0]),
            height_m=float(profile["height_m"][0]),
            dh_dx=float(profile["dh_dx"][0]),
            airspeed_mps=float(profile["airspeed_mps"][0]),
            dV_dx=float(profile["dV_dx"][0]),
            params=params,
            q3=q3,
        )
        return [rates["dm_dx"], rates["dt_dx"]]

    solution = solve_ivp(
        rhs,
        (0.0, q3.target_distance_m),
        np.array([params.m0_kg, 0.0]),
        t_eval=distance_nodes,
        rtol=1.0e-7,
        atol=1.0e-8,
        max_step=q3.target_distance_m / max(nodes - 1, 1),
    )
    if not solution.success:
        raise RuntimeError(solution.message)

    profile = _profile(distance_nodes, variables, reference_path=reference_path, q3=q3)
    records: list[dict[str, float]] = []
    max_violation = 0.0
    max_residual = 0.0
    for index, distance_m in enumerate(distance_nodes):
        rates = _rates_at(
            mass_kg=float(solution.y[0, index]),
            height_m=float(profile["height_m"][index]),
            dh_dx=float(profile["dh_dx"][index]),
            airspeed_mps=float(profile["airspeed_mps"][index]),
            dV_dx=float(profile["dV_dx"][index]),
            params=params,
            q3=q3,
        )
        max_violation = max(max_violation, rates["constraint_violation"])
        max_residual = max(max_residual, rates["path_residual"])
        records.append(
            {
                "distance_m": float(distance_m),
                "height_m": float(profile["height_m"][index]),
                "airspeed_mps": float(profile["airspeed_mps"][index]),
                "mass_kg": float(solution.y[0, index]),
                "time_s": float(solution.y[1, index]),
                **rates,
            }
        )
    final_mass = float(solution.y[0, -1])
    return PathEvaluation(
        trajectory=pd.DataFrame.from_records(records),
        final_mass_kg=final_mass,
        final_time_s=float(solution.y[1, -1]),
        terminal_mass_slack_kg=max(0.0, q3.terminal_mass_min_kg - final_mass),
        max_constraint_violation=max_violation,
        max_abs_path_residual=max_residual,
    )


def objective(
    variables: np.ndarray,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    reference_path: ReferencePath,
    nodes: int,
) -> float:
    try:
        result = evaluate_path(
            variables,
            q3=q3,
            params=params,
            reference_path=reference_path,
            nodes=nodes,
        )
    except (RuntimeError, ValueError, FloatingPointError):
        return 1.0e9
    return result.terminal_mass_slack_kg + 1.0e4 * result.max_constraint_violation**2


def solve_gate(q3: Q3Config, params: Q2Parameters, reference_path: ReferencePath, nodes: int) -> tuple[np.ndarray, PathEvaluation]:
    baseline_variables = np.zeros(4)
    starts = [
        baseline_variables,
        np.array([1900.0, 0.0, -5.5, -0.4]),
    ]
    bounds = [(-1500.0, 2200.0), (-1200.0, 1200.0), (-30.0, 10.0), (-12.0, 12.0)]
    best_x = baseline_variables
    best_value = math.inf
    objective_fn = lambda x: objective(  # noqa: E731
        x,
        q3=q3,
        params=params,
        reference_path=reference_path,
        nodes=nodes,
    )
    for start in starts:
        result = minimize(
            objective_fn,
            start,
            method="Powell",
            bounds=bounds,
            options={"maxiter": 35, "xtol": 1.0e-3, "ftol": 1.0e-3, "disp": False},
        )
        if result.fun < best_value:
            best_value = float(result.fun)
            best_x = np.asarray(result.x, dtype=float)
    return best_x, evaluate_path(best_x, q3=q3, params=params, reference_path=reference_path, nodes=nodes)


def trajectory_diagnostics(trajectory: pd.DataFrame, q3: Q3Config) -> dict[str, float]:
    height_lower_margin = trajectory["height_m"] - q3.h_min_m
    height_upper_margin = q3.h_max_m - trajectory["height_m"]
    airspeed_lower_margin = trajectory["airspeed_mps"] - q3.v_min_mps
    airspeed_upper_margin = q3.v_max_mps - trajectory["airspeed_mps"]
    thrust_lower_margin = trajectory["thrust_n"] - q3.thrust_min_n
    thrust_upper_margin = q3.thrust_max_n - trajectory["thrust_n"]
    gamma_margin = q3.gamma_max_rad - trajectory["gamma_rad"].abs()
    mach_margin = q3.mach_max - trajectory["mach"]
    return {
        "min_height_m": float(trajectory["height_m"].min()),
        "max_height_m": float(trajectory["height_m"].max()),
        "min_airspeed_mps": float(trajectory["airspeed_mps"].min()),
        "max_airspeed_mps": float(trajectory["airspeed_mps"].max()),
        "min_thrust_n": float(trajectory["thrust_n"].min()),
        "max_thrust_n": float(trajectory["thrust_n"].max()),
        "min_gamma_rad": float(trajectory["gamma_rad"].min()),
        "max_gamma_rad": float(trajectory["gamma_rad"].max()),
        "max_mach": float(trajectory["mach"].max()),
        "min_cl": float(trajectory["cl"].min()),
        "max_cl": float(trajectory["cl"].max()),
        "height_margin_min_m": float(pd.concat([height_lower_margin, height_upper_margin]).min()),
        "airspeed_margin_min_mps": float(pd.concat([airspeed_lower_margin, airspeed_upper_margin]).min()),
        "thrust_margin_min_n": float(pd.concat([thrust_lower_margin, thrust_upper_margin]).min()),
        "gamma_margin_min_rad": float(gamma_margin.min()),
        "mach_margin_min": float(mach_margin.min()),
    }


def fixed_path_shortfall_kg(root: Path, fallback: PathEvaluation, q3: Q3Config) -> float:
    table_path = root / "questions" / "q3" / "artifacts" / "tables" / "baseline_feasibility.csv"
    if table_path.exists():
        table = pd.read_csv(table_path)
        row = table.loc[table["wind_model"] == "no_wind"]
        if not row.empty and "final_mass_kg" in row.columns:
            return max(0.0, q3.terminal_mass_min_kg - float(row["final_mass_kg"].iloc[0]))
    return fallback.terminal_mass_slack_kg


def main() -> int:
    args = parse_args()
    if args.nodes < 7:
        raise ValueError("--nodes must be at least 7")
    root = project_root()
    q3 = load_q3_config(root, args.config)
    params = Q2Parameters(terminal_mass_kg=q3.terminal_mass_min_kg)
    reference_path = load_reference_path(str(root))

    fixed = evaluate_path(np.zeros(4), q3=q3, params=params, reference_path=reference_path, nodes=args.nodes)
    variables, solution = solve_gate(q3, params, reference_path, args.nodes)
    solver_status = "feasible" if solution.terminal_mass_slack_kg <= 1.0e-3 and solution.max_constraint_violation <= 1.0e-6 else "needs_relaxation"
    terminal = solution.trajectory.iloc[-1]
    diagnostics = trajectory_diagnostics(solution.trajectory, q3)
    summary = pd.DataFrame(
        [
            {
                "wind_model": "no_wind",
                "method": "range_domain_parameterized_feasibility_gate",
                "nodes": args.nodes,
                "solver_status": solver_status,
                "target_distance_m": q3.target_distance_m,
                "terminal_height_m": float(terminal["height_m"]),
                "terminal_height_error_m": float(terminal["height_m"]) - q3.terminal_height_m,
                "terminal_speed_mps": float(terminal["airspeed_mps"]),
                "terminal_speed_error_mps": float(terminal["airspeed_mps"]) - q3.terminal_airspeed_mps,
                "terminal_mass_kg": solution.final_mass_kg,
                "terminal_mass_min_kg": q3.terminal_mass_min_kg,
                "terminal_mass_shortfall_kg": solution.terminal_mass_slack_kg,
                "fixed_path_mass_shortfall_kg": fixed_path_shortfall_kg(root, fixed, q3),
                "fuel_used_kg": params.m0_kg - solution.final_mass_kg,
                "final_time_s": solution.final_time_s,
                "max_nonrelaxed_constraint_violation": solution.max_constraint_violation,
                "integration_consistency_residual": solution.max_abs_path_residual,
                **diagnostics,
                "h_sine_1_m": float(variables[0]),
                "h_sine_2_m": float(variables[1]),
                "v_sine_1_mps": float(variables[2]),
                "v_sine_2_mps": float(variables[3]),
            }
        ]
    )
    qdir = root / "questions" / "q3"
    save_table(summary, stem="no_wind_feasibility_gate", question_dir=qdir)
    save_table(solution.trajectory, stem="no_wind_feasibility_trajectory", question_dir=qdir)
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
