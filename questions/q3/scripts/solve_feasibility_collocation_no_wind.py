#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.integrate import solve_ivp
from scipy.optimize import minimize

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

H_SCALE_M = 10_000.0
V_SCALE_MPS = 240.0
M_SCALE_KG = 72_450.0
T_SCALE_N = 50_000.0
TIME_SCALE_S = 800.0
GAMMA_SCALE_RAD = 0.05
SLACK_SCALE_KG = 1_000.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q3 no-wind range-domain collocation feasibility gate")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--nodes", type=int, default=31)
    parser.add_argument(
        "--mesh-study-nodes",
        default="",
        help="comma-separated node counts for base-hmax reintegration mesh convergence diagnostics",
    )
    parser.add_argument(
        "--skip-hmax-sensitivity",
        action="store_true",
        help="skip the optimized h_max sensitivity sweep for focused formal or mesh-study runs",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="project the Gate 1 trajectory into the Gate 2 model without optimizing",
    )
    return parser.parse_args()


def _parse_mesh_nodes(value: str) -> list[int]:
    if not value.strip():
        return []
    nodes: list[int] = []
    for token in value.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        node_count = int(stripped)
        if node_count < 5:
            raise ValueError("--mesh-study-nodes entries must be at least 5")
        if node_count not in nodes:
            nodes.append(node_count)
    return nodes


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


def _state_rates_for_arrays(
    height_m: np.ndarray,
    airspeed_mps: np.ndarray,
    mass_kg: np.ndarray,
    thrust_n: np.ndarray,
    gamma_rad: np.ndarray,
    params: Q2Parameters,
) -> pd.DataFrame:
    records: list[dict[str, float]] = []
    for index in range(len(height_m)):
        records.append(
            _rates(
                height_m=float(height_m[index]),
                airspeed_mps=float(airspeed_mps[index]),
                mass_kg=float(mass_kg[index]),
                thrust_n=float(thrust_n[index]),
                gamma_rad=float(gamma_rad[index]),
                params=params,
                atmosphere_model=atmosphere,
            )
        )
    return pd.DataFrame.from_records(records)


def _pack_decision(
    *,
    height_m: np.ndarray,
    airspeed_mps: np.ndarray,
    mass_kg: np.ndarray,
    time_s: np.ndarray,
    thrust_n: np.ndarray,
    gamma_rad: np.ndarray,
    slack_kg: float,
) -> np.ndarray:
    return np.concatenate(
        [
            height_m / H_SCALE_M,
            airspeed_mps / V_SCALE_MPS,
            mass_kg / M_SCALE_KG,
            time_s / TIME_SCALE_S,
            thrust_n / T_SCALE_N,
            gamma_rad / GAMMA_SCALE_RAD,
            np.array([slack_kg / SLACK_SCALE_KG]),
        ]
    )


def _unpack_decision(vector: np.ndarray, nodes: int) -> dict[str, np.ndarray | float]:
    cursor = 0

    def take(scale: float) -> np.ndarray:
        nonlocal cursor
        values = vector[cursor : cursor + nodes] * scale
        cursor += nodes
        return values

    return {
        "height_m": take(H_SCALE_M),
        "airspeed_mps": take(V_SCALE_MPS),
        "mass_kg": take(M_SCALE_KG),
        "time_s": take(TIME_SCALE_S),
        "thrust_n": take(T_SCALE_N),
        "gamma_rad": take(GAMMA_SCALE_RAD),
        "slack_kg": float(vector[cursor] * SLACK_SCALE_KG),
    }


def _decision_to_trajectory(vector: np.ndarray, *, nodes: int, q3: Q3Config, params: Q2Parameters) -> pd.DataFrame:
    values = _unpack_decision(vector, nodes)
    distance = np.linspace(0.0, q3.target_distance_m, nodes)
    rates = _state_rates_for_arrays(
        values["height_m"],
        values["airspeed_mps"],
        values["mass_kg"],
        values["thrust_n"],
        values["gamma_rad"],
        params,
    )
    trajectory = pd.DataFrame(
        {
            "distance_m": distance,
            "height_m": values["height_m"],
            "airspeed_mps": values["airspeed_mps"],
            "mass_kg": values["mass_kg"],
            "time_s": values["time_s"],
            "thrust_n": values["thrust_n"],
            "gamma_rad": values["gamma_rad"],
        }
    )
    return pd.concat([trajectory, rates], axis=1)


def _formal_collocation_diagnostics(trajectory: pd.DataFrame, q3: Q3Config) -> dict[str, float]:
    diagnostics = _collocation_diagnostics(trajectory, q3)
    height = trajectory["height_m"].to_numpy(dtype=float)
    max_reconstruction_violation = 0.0
    for index in range(len(height) - 1):
        samples = np.linspace(height[index], height[index + 1], 7)
        max_reconstruction_violation = max(
            max_reconstruction_violation,
            float(np.max(np.maximum(0.0, samples - q3.h_max_m))),
        )
    diagnostics["max_reconstruction_height_violation_m"] = max_reconstruction_violation
    return diagnostics


def _collocation_equalities(vector: np.ndarray, *, nodes: int, q3: Q3Config, params: Q2Parameters) -> np.ndarray:
    values = _unpack_decision(vector, nodes)
    rates = _state_rates_for_arrays(
        values["height_m"],
        values["airspeed_mps"],
        values["mass_kg"],
        values["thrust_n"],
        values["gamma_rad"],
        params,
    )[["dh_dx", "dV_dx", "dm_dx", "dt_dx"]].to_numpy(dtype=float)
    distance = np.linspace(0.0, q3.target_distance_m, nodes)
    equalities = [
        (values["height_m"][0] - 9500.0) / H_SCALE_M,
        (values["airspeed_mps"][0] - q3.terminal_airspeed_mps) / V_SCALE_MPS,
        (values["mass_kg"][0] - params.m0_kg) / M_SCALE_KG,
        values["time_s"][0] / TIME_SCALE_S,
        (values["height_m"][-1] - q3.terminal_height_m) / H_SCALE_M,
        (values["airspeed_mps"][-1] - q3.terminal_airspeed_mps) / V_SCALE_MPS,
    ]
    state_values = np.column_stack(
        [values["height_m"], values["airspeed_mps"], values["mass_kg"], values["time_s"]]
    )
    scales = np.array([H_SCALE_M, V_SCALE_MPS, M_SCALE_KG, TIME_SCALE_S])
    for index in range(nodes - 1):
        dx = distance[index + 1] - distance[index]
        defect = state_values[index + 1] - state_values[index] - 0.5 * dx * (rates[index] + rates[index + 1])
        equalities.extend((defect / scales).tolist())
    return np.asarray(equalities, dtype=float)


def _collocation_inequalities(vector: np.ndarray, *, nodes: int, q3: Q3Config, params: Q2Parameters) -> np.ndarray:
    values = _unpack_decision(vector, nodes)
    rates = _state_rates_for_arrays(
        values["height_m"],
        values["airspeed_mps"],
        values["mass_kg"],
        values["thrust_n"],
        values["gamma_rad"],
        params,
    )
    inequalities: list[float] = [
        values["mass_kg"][-1] + values["slack_kg"] - q3.terminal_mass_min_kg,
        values["slack_kg"],
    ]
    inequalities.extend((q3.mach_max - rates["mach"].to_numpy(dtype=float)).tolist())
    midpoint_height = 0.5 * (values["height_m"][:-1] + values["height_m"][1:])
    inequalities.extend((q3.h_max_m - midpoint_height).tolist())
    return np.asarray(inequalities, dtype=float)


def _decision_bounds(nodes: int, q3: Q3Config) -> list[tuple[float, float]]:
    return (
        [(q3.h_min_m / H_SCALE_M, q3.h_max_m / H_SCALE_M)] * nodes
        + [(q3.v_min_mps / V_SCALE_MPS, q3.v_max_mps / V_SCALE_MPS)] * nodes
        + [(55_000.0 / M_SCALE_KG, 73_000.0 / M_SCALE_KG)] * nodes
        + [(0.0, 2_000.0 / TIME_SCALE_S)] * nodes
        + [(q3.thrust_min_n / T_SCALE_N, q3.thrust_max_n / T_SCALE_N)] * nodes
        + [(-q3.gamma_max_rad / GAMMA_SCALE_RAD, q3.gamma_max_rad / GAMMA_SCALE_RAD)] * nodes
        + [(0.0, 2_000.0 / SLACK_SCALE_KG)]
    )


def _initial_decision_from_warm_start(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
) -> np.ndarray:
    warm = _project_gate1_warm_start(gate1, q3=q3, params=params, nodes=nodes)
    slack = max(0.0, q3.terminal_mass_min_kg - float(warm["mass_kg"].iloc[-1]))
    return _pack_decision(
        height_m=warm["height_m"].to_numpy(dtype=float),
        airspeed_mps=warm["airspeed_mps"].to_numpy(dtype=float),
        mass_kg=warm["mass_kg"].to_numpy(dtype=float),
        time_s=warm["time_s"].to_numpy(dtype=float),
        thrust_n=warm["thrust_n"].to_numpy(dtype=float),
        gamma_rad=warm["gamma_rad"].to_numpy(dtype=float),
        slack_kg=slack,
    )


def _solve_stage1_collocation(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    maxiter: int = 180,
) -> tuple[np.ndarray, object]:
    initial = _initial_decision_from_warm_start(gate1, q3=q3, params=params, nodes=nodes)

    def objective(vector: np.ndarray) -> float:
        return float(_unpack_decision(vector, nodes)["slack_kg"]) / SLACK_SCALE_KG

    constraints = [
        {
            "type": "eq",
            "fun": lambda vector: _collocation_equalities(vector, nodes=nodes, q3=q3, params=params),
        },
        {
            "type": "ineq",
            "fun": lambda vector: _collocation_inequalities(vector, nodes=nodes, q3=q3, params=params),
        },
    ]
    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=_decision_bounds(nodes, q3),
        constraints=constraints,
        options={"maxiter": maxiter, "ftol": 1.0e-9, "disp": False},
    )
    vector = np.asarray(result.x if hasattr(result, "x") else initial, dtype=float)
    return vector, result


def _reintegration_diagnostics(
    trajectory: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
) -> dict[str, float | str]:
    distance = trajectory["distance_m"].to_numpy(dtype=float)
    thrust = trajectory["thrust_n"].to_numpy(dtype=float)
    gamma = trajectory["gamma_rad"].to_numpy(dtype=float)

    def rhs(distance_m: float, state: np.ndarray) -> list[float]:
        thrust_n = float(np.interp(distance_m, distance, thrust))
        gamma_rad = float(np.interp(distance_m, distance, gamma))
        rates = _rates(
            height_m=float(state[0]),
            airspeed_mps=float(state[1]),
            mass_kg=float(state[2]),
            thrust_n=thrust_n,
            gamma_rad=gamma_rad,
            params=params,
            atmosphere_model=atmosphere,
        )
        return [rates["dh_dx"], rates["dV_dx"], rates["dm_dx"], rates["dt_dx"]]

    solution = solve_ivp(
        rhs,
        (float(distance[0]), float(distance[-1])),
        np.array([9500.0, q3.terminal_airspeed_mps, params.m0_kg, 0.0]),
        t_eval=distance,
        dense_output=True,
        rtol=1.0e-8,
        atol=np.array([1.0e-5, 1.0e-7, 1.0e-4, 1.0e-6]),
        max_step=q3.target_distance_m / max(len(distance) - 1, 1) / 4.0,
    )
    if not solution.success:
        return {
            "control_reconstruction": "piecewise_linear_node_controls",
            "reintegration_state_error_inf": math.inf,
            "reintegration_terminal_mass_kg": math.inf,
            "reintegration_terminal_mass_signed_error_kg": math.inf,
            "reintegration_terminal_mass_error_kg": math.inf,
            "reintegration_terminal_mass_shortfall_kg": math.inf,
            "reintegration_terminal_height_signed_error_m": math.inf,
            "reintegration_terminal_height_error_m": math.inf,
            "reintegration_terminal_speed_signed_error_mps": math.inf,
            "reintegration_terminal_speed_error_mps": math.inf,
            "reintegration_max_scaled_constraint_violation": math.inf,
            "reintegration_max_node_speed_signed_error_mps": math.inf,
            "reintegration_max_node_speed_error_mps": math.inf,
            "reintegration_max_node_mass_signed_error_kg": math.inf,
            "reintegration_max_node_mass_error_kg": math.inf,
        }
    collocation_states = trajectory[["height_m", "airspeed_mps", "mass_kg", "time_s"]].to_numpy(dtype=float).T
    errors = solution.y - collocation_states
    scaled = np.vstack(
        [
            errors[0] / H_SCALE_M,
            errors[1] / V_SCALE_MPS,
            errors[2] / M_SCALE_KG,
            errors[3] / TIME_SCALE_S,
        ]
    )
    dense_distance = np.linspace(float(distance[0]), float(distance[-1]), max(4 * (len(distance) - 1) + 1, len(distance)))
    dense_states = solution.sol(dense_distance) if solution.sol is not None else np.interp(dense_distance, solution.t, solution.y)
    dense_violations: list[float] = []
    for index, distance_m in enumerate(dense_distance):
        thrust_n = float(np.interp(distance_m, distance, thrust))
        gamma_rad = float(np.interp(distance_m, distance, gamma))
        rates = _rates(
            height_m=float(dense_states[0, index]),
            airspeed_mps=float(dense_states[1, index]),
            mass_kg=float(dense_states[2, index]),
            thrust_n=thrust_n,
            gamma_rad=gamma_rad,
            params=params,
            atmosphere_model=atmosphere,
        )
        dense_violations.append(
            max(
                0.0,
                (q3.h_min_m - float(dense_states[0, index])) / H_SCALE_M,
                (float(dense_states[0, index]) - q3.h_max_m) / H_SCALE_M,
                (q3.v_min_mps - float(dense_states[1, index])) / V_SCALE_MPS,
                (float(dense_states[1, index]) - q3.v_max_mps) / V_SCALE_MPS,
                (q3.terminal_mass_min_kg - float(dense_states[2, index])) / M_SCALE_KG,
                (q3.thrust_min_n - thrust_n) / max(q3.thrust_max_n, 1.0),
                (thrust_n - q3.thrust_max_n) / max(q3.thrust_max_n, 1.0),
                (abs(gamma_rad) - q3.gamma_max_rad) / max(q3.gamma_max_rad, 1.0e-9),
                rates["mach"] - q3.mach_max,
            )
        )
    reintegrated_h = float(solution.y[0, -1])
    reintegrated_v = float(solution.y[1, -1])
    reintegrated_m = float(solution.y[2, -1])
    collocation_final_mass = float(collocation_states[2, -1])
    node_speed_errors = errors[1]
    node_mass_errors = errors[2]
    max_speed_index = int(np.argmax(np.abs(node_speed_errors)))
    max_mass_index = int(np.argmax(np.abs(node_mass_errors)))
    return {
        "control_reconstruction": "piecewise_linear_node_controls",
        "reintegration_state_error_inf": float(np.max(np.abs(scaled))),
        "reintegration_terminal_mass_kg": reintegrated_m,
        "reintegration_terminal_mass_signed_error_kg": reintegrated_m - collocation_final_mass,
        "reintegration_terminal_mass_error_kg": abs(reintegrated_m - collocation_final_mass),
        "reintegration_terminal_mass_shortfall_kg": max(0.0, q3.terminal_mass_min_kg - reintegrated_m),
        "reintegration_terminal_height_signed_error_m": reintegrated_h - q3.terminal_height_m,
        "reintegration_terminal_height_error_m": abs(reintegrated_h - q3.terminal_height_m),
        "reintegration_terminal_speed_signed_error_mps": reintegrated_v - q3.terminal_airspeed_mps,
        "reintegration_terminal_speed_error_mps": abs(reintegrated_v - q3.terminal_airspeed_mps),
        "reintegration_max_scaled_constraint_violation": float(max(dense_violations)) if dense_violations else 0.0,
        "reintegration_max_node_speed_signed_error_mps": float(node_speed_errors[max_speed_index]),
        "reintegration_max_node_speed_error_mps": float(abs(node_speed_errors[max_speed_index])),
        "reintegration_max_node_mass_signed_error_kg": float(node_mass_errors[max_mass_index]),
        "reintegration_max_node_mass_error_kg": float(abs(node_mass_errors[max_mass_index])),
    }


def _formal_solver_status(
    *,
    result: object,
    slack_kg: float,
    diagnostics: dict[str, float],
    reintegration: dict[str, float | str],
    max_scaled_constraint_violation: float,
    q3: Q3Config,
    gate_config: dict,
) -> str:
    if not getattr(result, "success", False):
        return "optimization_failed"
    criteria = gate_config["pass_criteria"]
    discrete_feasible = (
        slack_kg <= float(criteria["terminal_mass_shortfall_kg"])
        and diagnostics["scaled_collocation_defect_inf"] <= float(criteria["scaled_collocation_defect_inf"])
        and diagnostics["max_midpoint_height_violation_m"] <= 1.0e-9
        and max_scaled_constraint_violation <= float(criteria["constraint_violation_tolerance"])
    )
    reintegration_feasible = (
        float(reintegration["reintegration_terminal_mass_shortfall_kg"])
        <= float(criteria["terminal_mass_shortfall_kg"])
        and float(reintegration["reintegration_terminal_height_error_m"]) <= float(criteria["terminal_height_error_m"])
        and float(reintegration["reintegration_terminal_speed_error_mps"]) <= float(criteria["terminal_airspeed_error_mps"])
        and float(reintegration["reintegration_max_scaled_constraint_violation"])
        <= float(criteria["constraint_violation_tolerance"])
    )
    if discrete_feasible and reintegration_feasible:
        return "gate2_feasible"
    if discrete_feasible:
        return "discrete_feasible_reintegration_failed"
    return "needs_relaxation"


def _control_variation_metrics(trajectory: pd.DataFrame) -> dict[str, float]:
    thrust = trajectory["thrust_n"].to_numpy(dtype=float)
    gamma = trajectory["gamma_rad"].to_numpy(dtype=float)
    thrust_steps = np.abs(np.diff(thrust))
    gamma_steps = np.abs(np.diff(gamma))
    return {
        "max_thrust_step_n": float(np.max(thrust_steps)) if len(thrust_steps) else 0.0,
        "max_gamma_step_rad": float(np.max(gamma_steps)) if len(gamma_steps) else 0.0,
        "total_variation_thrust_n": float(np.sum(thrust_steps)),
        "total_variation_gamma_rad": float(np.sum(gamma_steps)),
    }


def _formal_gate_case(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    gate_config: dict,
    maxiter: int = 180,
) -> tuple[pd.DataFrame, dict[str, float | str | bool]]:
    vector, optimizer_result = _solve_stage1_collocation(
        gate1,
        q3=q3,
        params=params,
        nodes=nodes,
        maxiter=maxiter,
    )
    trajectory = _decision_to_trajectory(vector, nodes=nodes, q3=q3, params=params)
    trajectory["scaled_constraint_violation"] = trajectory.apply(_scaled_constraint_violation, axis=1, q3=q3)
    values = _unpack_decision(vector, nodes)
    diagnostics = _formal_collocation_diagnostics(trajectory, q3)
    reintegration = _reintegration_diagnostics(trajectory, q3=q3, params=params)
    max_scaled_violation = float(trajectory["scaled_constraint_violation"].max())
    slack_kg = max(0.0, float(values["slack_kg"]))
    final = trajectory.iloc[-1]
    atmosphere_deviation = max_deviation_from_layered_isa()
    solver_status = _formal_solver_status(
        result=optimizer_result,
        slack_kg=slack_kg,
        diagnostics=diagnostics,
        reintegration=reintegration,
        max_scaled_constraint_violation=max_scaled_violation,
        q3=q3,
        gate_config=gate_config,
    )
    return trajectory, {
        "wind_model": "no_wind",
        "method": "range_domain_collocation_feasibility_gate",
        "nodes": nodes,
        "solver_status": solver_status,
        "optimizer_success": bool(getattr(optimizer_result, "success", False)),
        "optimizer_message": str(getattr(optimizer_result, "message", "")),
        "lexicographic_stage": "stage1_minimize_terminal_mass_slack",
        "mass_constraint_policy": "m_f_plus_s_ge_62000_s_ge_0",
        "atmosphere_model": "C1_temperature_hydrostatic_pressure",
        "terminal_mass_kg": float(final["mass_kg"]),
        "terminal_mass_min_kg": q3.terminal_mass_min_kg,
        "terminal_mass_slack_kg": slack_kg,
        "terminal_mass_shortfall_kg": max(0.0, q3.terminal_mass_min_kg - float(final["mass_kg"])),
        "terminal_height_error_m": abs(float(final["height_m"] - q3.terminal_height_m)),
        "terminal_speed_error_mps": abs(float(final["airspeed_mps"] - q3.terminal_airspeed_mps)),
        "fuel_used_kg": params.m0_kg - float(final["mass_kg"]),
        "final_time_s": float(final["time_s"]),
        "max_scaled_constraint_violation": max_scaled_violation,
        "constraint_violation_scale": "nondimensional",
        **diagnostics,
        **reintegration,
        **atmosphere_deviation,
    }


def _error_ratio(previous: float | None, current: float) -> float:
    if previous is None or not np.isfinite(previous) or not np.isfinite(current):
        return math.nan
    if current == 0.0:
        return math.inf if previous > 0.0 else math.nan
    return previous / current


def _mesh_convergence_study(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes_list: list[int],
    gate_config: dict,
    precomputed_cases: dict[int, tuple[pd.DataFrame, dict[str, float | str | bool]]] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, float | str | bool]] = []
    previous_mass_error: float | None = None
    previous_speed_error: float | None = None
    precomputed_cases = precomputed_cases or {}
    for node_count in nodes_list:
        if node_count in precomputed_cases:
            trajectory, summary = precomputed_cases[node_count]
        else:
            trajectory, summary = _formal_gate_case(
                gate1,
                q3=q3,
                params=params,
                nodes=node_count,
                gate_config=gate_config,
            )
        mass_error = float(summary["reintegration_terminal_mass_error_kg"])
        speed_error = float(summary["reintegration_terminal_speed_error_mps"])
        rows.append(
            {
                "nodes": node_count,
                "h_max_m": q3.h_max_m,
                "terminal_mass_kg": float(summary["terminal_mass_kg"]),
                "terminal_mass_slack_kg": float(summary["terminal_mass_slack_kg"]),
                "final_time_s": float(summary["final_time_s"]),
                "scaled_collocation_defect_inf": float(summary["scaled_collocation_defect_inf"]),
                "max_scaled_constraint_violation": float(summary["max_scaled_constraint_violation"]),
                "reintegration_state_error_inf": float(summary["reintegration_state_error_inf"]),
                "reintegration_terminal_mass_kg": float(summary["reintegration_terminal_mass_kg"]),
                "reintegration_terminal_mass_signed_error_kg": float(
                    summary["reintegration_terminal_mass_signed_error_kg"]
                ),
                "reintegration_terminal_mass_error_kg": mass_error,
                "reintegration_terminal_mass_shortfall_kg": float(
                    summary["reintegration_terminal_mass_shortfall_kg"]
                ),
                "reintegration_terminal_height_signed_error_m": float(
                    summary["reintegration_terminal_height_signed_error_m"]
                ),
                "reintegration_terminal_height_error_m": float(summary["reintegration_terminal_height_error_m"]),
                "reintegration_terminal_speed_signed_error_mps": float(
                    summary["reintegration_terminal_speed_signed_error_mps"]
                ),
                "terminal_speed_signed_error_mps": float(summary["reintegration_terminal_speed_signed_error_mps"]),
                "reintegration_terminal_speed_error_mps": speed_error,
                "mass_error_ratio_from_previous": _error_ratio(previous_mass_error, mass_error),
                "speed_error_ratio_from_previous": _error_ratio(previous_speed_error, speed_error),
                **_control_variation_metrics(trajectory),
                "max_node_speed_signed_error_mps": float(
                    summary["reintegration_max_node_speed_signed_error_mps"]
                ),
                "max_node_speed_error_mps": float(summary["reintegration_max_node_speed_error_mps"]),
                "max_node_mass_signed_error_kg": float(summary["reintegration_max_node_mass_signed_error_kg"]),
                "max_node_mass_error_kg": float(summary["reintegration_max_node_mass_error_kg"]),
                "gate_status": str(summary["solver_status"]),
                "optimizer_success": bool(summary["optimizer_success"]),
            }
        )
        previous_mass_error = mass_error
        previous_speed_error = speed_error
    return pd.DataFrame(rows)


def _optimized_hmax_sensitivity(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    hmax_values: list[float],
    gate_config: dict,
) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for hmax in hmax_values:
        local_q3 = replace(q3, h_max_m=float(hmax))
        vector, result = _solve_stage1_collocation(gate1, q3=local_q3, params=params, nodes=nodes, maxiter=60)
        trajectory = _decision_to_trajectory(vector, nodes=nodes, q3=local_q3, params=params)
        trajectory["scaled_constraint_violation"] = trajectory.apply(_scaled_constraint_violation, axis=1, q3=local_q3)
        values = _unpack_decision(vector, nodes)
        diagnostics = _formal_collocation_diagnostics(trajectory, local_q3)
        reintegration = _reintegration_diagnostics(trajectory, q3=local_q3, params=params)
        max_scaled_violation = float(trajectory["scaled_constraint_violation"].max())
        status = _formal_solver_status(
            result=result,
            slack_kg=max(0.0, float(values["slack_kg"])),
            diagnostics=diagnostics,
            reintegration=reintegration,
            max_scaled_constraint_violation=max_scaled_violation,
            q3=local_q3,
            gate_config=gate_config,
        )
        rows.append(
            {
                "h_max_m": float(hmax),
                "nodes": nodes,
                "terminal_mass_kg": float(trajectory["mass_kg"].iloc[-1]),
                "terminal_mass_slack_kg": max(0.0, float(values["slack_kg"])),
                "final_time_s": float(trajectory["time_s"].iloc[-1]),
                "max_height_m": float(trajectory["height_m"].max()),
                "max_height_violation_m": max(0.0, float(trajectory["height_m"].max()) - float(hmax)),
                "scaled_collocation_defect_inf": diagnostics["scaled_collocation_defect_inf"],
                "max_scaled_constraint_violation": max_scaled_violation,
                "reintegration_terminal_mass_kg": float(reintegration["reintegration_terminal_mass_kg"]),
                "reintegration_terminal_mass_signed_error_kg": float(
                    reintegration["reintegration_terminal_mass_signed_error_kg"]
                ),
                "reintegration_terminal_mass_shortfall_kg": float(
                    reintegration["reintegration_terminal_mass_shortfall_kg"]
                ),
                "reintegration_terminal_height_error_m": float(reintegration["reintegration_terminal_height_error_m"]),
                "reintegration_terminal_speed_error_mps": float(reintegration["reintegration_terminal_speed_error_mps"]),
                "active_hmax_fraction": float(np.mean(np.isclose(trajectory["height_m"], float(hmax), atol=1.0))),
                "gate_status": status,
                "status": status,
            }
        )
    return pd.DataFrame(rows)


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
    mesh_nodes = _parse_mesh_nodes(args.mesh_study_nodes)

    root = project_root()
    q3 = load_q3_config(root, args.config)
    gate_config = _load_gate_config(root, args.config)
    params = Q2Parameters(terminal_mass_kg=q3.terminal_mass_min_kg)
    gate1 = _gate1_trajectory(root)
    qdir = root / "questions" / "q3"

    if not args.dry_run:
        trajectory, summary_row = _formal_gate_case(
            gate1,
            q3=q3,
            params=params,
            nodes=args.nodes,
            gate_config=gate_config,
        )
        summary = pd.DataFrame([summary_row])
        save_table(summary, stem="no_wind_collocation_formal_gate", question_dir=qdir)
        save_table(trajectory, stem="no_wind_collocation_formal_trajectory", question_dir=qdir)
        if not args.skip_hmax_sensitivity:
            save_table(
                _optimized_hmax_sensitivity(
                    gate1,
                    q3=q3,
                    params=params,
                    nodes=args.nodes,
                    hmax_values=[float(x) for x in gate_config["hmax_sensitivity_m"]],
                    gate_config=gate_config,
                ),
                stem="optimized_hmax_sensitivity",
                question_dir=qdir,
            )
        if mesh_nodes:
            save_table(
                _mesh_convergence_study(
                    gate1,
                    q3=q3,
                    params=params,
                    nodes_list=mesh_nodes,
                    gate_config=gate_config,
                    precomputed_cases={args.nodes: (trajectory, summary_row)},
                ),
                stem="no_wind_collocation_mesh_convergence",
                question_dir=qdir,
            )
        save_table(
            smoothing_diagnostics_table(),
            stem="atmosphere_smoothing_diagnostics",
            question_dir=qdir,
        )
        save_table(
            _atmosphere_coupling_diagnostics(params),
            stem="atmosphere_coupling_diagnostics",
            question_dir=qdir,
        )
        print(summary.to_string(index=False))
        return 0

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
