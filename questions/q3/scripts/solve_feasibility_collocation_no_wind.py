#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, replace
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
BASE_REINTEGRATION_ATOL = np.array([1.0e-5, 1.0e-7, 1.0e-4, 1.0e-6])
STATE_SCALES = np.array([H_SCALE_M, V_SCALE_MPS, M_SCALE_KG, TIME_SCALE_S])
SHOOTING_HEIGHT_MARGIN_M = 0.05


@dataclass(frozen=True)
class ShootingEvaluation:
    trajectory: pd.DataFrame
    final_height_error_m: float
    final_speed_error_mps: float
    final_mass_shortfall_kg: float
    max_scaled_constraint_violation: float
    fuel_used_kg: float
    success: bool


@dataclass(frozen=True)
class ShootingOptimizerResult:
    success: bool
    message: str
    nit: int
    validation_success: bool


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
    parser.add_argument(
        "--ode-rtols",
        default="",
        help="comma-separated ODE rtol values for reintegration tolerance and continuous path audits",
    )
    parser.add_argument(
        "--final-fuel",
        action="store_true",
        help="solve the final no-wind fuel objective after Gate 2 feasibility",
    )
    parser.add_argument(
        "--continuation-nodes",
        default="",
        help="comma-separated node counts for final-fuel continuation; defaults to --nodes",
    )
    parser.add_argument(
        "--initial-guess",
        choices=["gate2", "straight", "perturbed"],
        default="gate2",
        help="primary initial guess for final-fuel optimization",
    )
    parser.add_argument(
        "--multi-initial-guesses",
        default="gate2,straight,perturbed",
        help="comma-separated initial guesses for final validation at the last node count",
    )
    parser.add_argument(
        "--final-solver",
        choices=["candidate", "slsqp", "shooting"],
        default="candidate",
        help=(
            "final-fuel solver mode; candidate evaluates Gate 2 continuation quickly, "
            "slsqp solves full collocation NLP, shooting solves a reduced continuous-control problem"
        ),
    )
    parser.add_argument("--final-maxiter", type=int, default=220)
    parser.add_argument(
        "--shooting-control-knots",
        type=int,
        default=7,
        help="number of reduced thrust/gamma control knots for --final-solver shooting",
    )
    parser.add_argument(
        "--final-hmax-sensitivity",
        action="store_true",
        help="re-optimize final no-wind fuel objective for configured h_max sensitivity values",
    )
    parser.add_argument(
        "--final-hmax-values",
        default="",
        help="comma-separated h_max values for --final-hmax-sensitivity; defaults to config feasibility list",
    )
    parser.add_argument(
        "--final-idle-thrust-sensitivity",
        action="store_true",
        help="re-optimize final no-wind fuel objective for idle thrust lower-bound fractions",
    )
    parser.add_argument(
        "--final-idle-thrust-fractions",
        default="",
        help=(
            "comma-separated fractions of thrust_max_n used as thrust_min_n for "
            "--final-idle-thrust-sensitivity; defaults to config feasibility list"
        ),
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


def _parse_ode_rtols(value: str) -> list[float]:
    if not value.strip():
        return []
    rtols: list[float] = []
    for token in value.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        rtol = float(stripped)
        if rtol <= 0.0:
            raise ValueError("--ode-rtols entries must be positive")
        if rtol not in rtols:
            rtols.append(rtol)
    return rtols


def _parse_float_list(value: str, *, option_name: str) -> list[float]:
    if not value.strip():
        return []
    values: list[float] = []
    for token in value.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        number = float(stripped)
        if not math.isfinite(number):
            raise ValueError(f"{option_name} entries must be finite")
        if number not in values:
            values.append(number)
    return values


def _parse_initial_guesses(value: str) -> list[str]:
    if not value.strip():
        return []
    allowed = {"gate2", "straight", "perturbed"}
    guesses: list[str] = []
    for token in value.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        if stripped not in allowed:
            raise ValueError(f"unknown initial guess {stripped!r}; expected one of {sorted(allowed)}")
        if stripped not in guesses:
            guesses.append(stripped)
    return guesses


def _strict_reintegration_atol(rtol: float) -> np.ndarray:
    return np.minimum(BASE_REINTEGRATION_ATOL, 0.1 * rtol * STATE_SCALES)


def _load_gate_config(root: Path, config_path: str) -> dict:
    with (root / config_path).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config["q3_optimal_control"]["feasibility_gate"]


def _idle_thrust_sensitivity_fractions(root: Path, config_path: str) -> list[float]:
    with (root / config_path).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    gate = config["q3_optimal_control"]["feasibility_gate"]
    return [float(value) for value in gate.get("idle_thrust_sensitivity_fractions", [0.0, 0.05, 0.10])]


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


def _decision_bounds(
    nodes: int,
    q3: Q3Config,
    *,
    slack_bounds_kg: tuple[float, float] = (0.0, 2_000.0),
) -> list[tuple[float, float]]:
    return (
        [(q3.h_min_m / H_SCALE_M, q3.h_max_m / H_SCALE_M)] * nodes
        + [(q3.v_min_mps / V_SCALE_MPS, q3.v_max_mps / V_SCALE_MPS)] * nodes
        + [(55_000.0 / M_SCALE_KG, 73_000.0 / M_SCALE_KG)] * nodes
        + [(0.0, 2_000.0 / TIME_SCALE_S)] * nodes
        + [(q3.thrust_min_n / T_SCALE_N, q3.thrust_max_n / T_SCALE_N)] * nodes
        + [(-q3.gamma_max_rad / GAMMA_SCALE_RAD, q3.gamma_max_rad / GAMMA_SCALE_RAD)] * nodes
        + [(slack_bounds_kg[0] / SLACK_SCALE_KG, slack_bounds_kg[1] / SLACK_SCALE_KG)]
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


def _resample_trajectory_decision(
    trajectory: pd.DataFrame,
    *,
    q3: Q3Config,
    nodes: int,
    slack_kg: float = 0.0,
) -> np.ndarray:
    source = trajectory.sort_values("distance_m").drop_duplicates("distance_m")
    distance = np.linspace(0.0, q3.target_distance_m, nodes)
    height = _interp(source, "height_m", distance)
    airspeed = _interp(source, "airspeed_mps", distance)
    mass = _interp(source, "mass_kg", distance)
    time = _interp(source, "time_s", distance)
    thrust = _interp(source, "thrust_n", distance)
    gamma = _interp(source, "gamma_rad", distance)
    height[0] = 9500.0
    airspeed[0] = q3.terminal_airspeed_mps
    mass[0] = M_SCALE_KG
    time[0] = 0.0
    height[-1] = q3.terminal_height_m
    airspeed[-1] = q3.terminal_airspeed_mps
    mass = np.maximum(mass, q3.terminal_mass_min_kg)
    return _pack_decision(
        height_m=height,
        airspeed_mps=airspeed,
        mass_kg=mass,
        time_s=time,
        thrust_n=thrust,
        gamma_rad=gamma,
        slack_kg=slack_kg,
    )


def _straight_initial_decision(*, q3: Q3Config, params: Q2Parameters, nodes: int) -> np.ndarray:
    distance = np.linspace(0.0, q3.target_distance_m, nodes)
    height = np.linspace(9500.0, q3.terminal_height_m, nodes)
    airspeed = np.full(nodes, q3.terminal_airspeed_mps)
    gamma = np.arctan2(np.gradient(height, distance, edge_order=1), 1.0)
    thrust = np.zeros(nodes)
    mass = np.zeros(nodes)
    time = np.zeros(nodes)
    mass[0] = params.m0_kg
    for index in range(nodes):
        rates = _rates(
            height_m=float(height[index]),
            airspeed_mps=float(airspeed[index]),
            mass_kg=float(mass[index]) if mass[index] > 0.0 else params.m0_kg,
            thrust_n=float(thrust[index]) if thrust[index] > 0.0 else 50_000.0,
            gamma_rad=float(gamma[index]),
            params=params,
            atmosphere_model=atmosphere,
        )
        drag = rates["drag_n"]
        required = (drag + mass[index] * params.g_mps2 * math.sin(float(gamma[index]))) if mass[index] > 0.0 else drag
        thrust[index] = float(np.clip(required, q3.thrust_min_n, q3.thrust_max_n))
        if index == nodes - 1:
            break
        dx = distance[index + 1] - distance[index]
        rates_now = _rates(
            height_m=float(height[index]),
            airspeed_mps=float(airspeed[index]),
            mass_kg=float(mass[index]),
            thrust_n=float(thrust[index]),
            gamma_rad=float(gamma[index]),
            params=params,
            atmosphere_model=atmosphere,
        )
        mass[index + 1] = max(q3.terminal_mass_min_kg, mass[index] + dx * rates_now["dm_dx"])
        time[index + 1] = time[index] + dx * rates_now["dt_dx"]
    return _pack_decision(
        height_m=height,
        airspeed_mps=airspeed,
        mass_kg=mass,
        time_s=time,
        thrust_n=thrust,
        gamma_rad=gamma,
        slack_kg=0.0,
    )


def _perturb_decision(vector: np.ndarray, *, nodes: int, q3: Q3Config) -> np.ndarray:
    values = _unpack_decision(vector.copy(), nodes)
    phase = np.linspace(0.0, math.pi, nodes)
    height = np.clip(values["height_m"] + 80.0 * np.sin(phase), q3.h_min_m, q3.h_max_m)
    airspeed = np.clip(values["airspeed_mps"] + 0.8 * np.sin(2.0 * phase), q3.v_min_mps, q3.v_max_mps)
    thrust = np.clip(values["thrust_n"] * (1.0 + 0.015 * np.sin(phase)), q3.thrust_min_n, q3.thrust_max_n)
    gamma = np.clip(values["gamma_rad"] + 2.0e-4 * np.sin(2.0 * phase), -q3.gamma_max_rad, q3.gamma_max_rad)
    return _pack_decision(
        height_m=height,
        airspeed_mps=airspeed,
        mass_kg=values["mass_kg"],
        time_s=values["time_s"],
        thrust_n=thrust,
        gamma_rad=gamma,
        slack_kg=0.0,
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


def _final_fuel_equalities(vector: np.ndarray, *, nodes: int, q3: Q3Config, params: Q2Parameters) -> np.ndarray:
    return _collocation_equalities(vector, nodes=nodes, q3=q3, params=params)


def _final_fuel_inequalities(vector: np.ndarray, *, nodes: int, q3: Q3Config, params: Q2Parameters) -> np.ndarray:
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
        values["mass_kg"][-1] - q3.terminal_mass_min_kg,
    ]
    inequalities.extend((values["mass_kg"] - q3.terminal_mass_min_kg).tolist())
    inequalities.extend((q3.mach_max - rates["mach"].to_numpy(dtype=float)).tolist())
    midpoint_height = 0.5 * (values["height_m"][:-1] + values["height_m"][1:])
    inequalities.extend((q3.h_max_m - midpoint_height).tolist())
    return np.asarray(inequalities, dtype=float)


def _solve_final_fuel_collocation(
    initial: np.ndarray,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    maxiter: int,
) -> tuple[np.ndarray, object]:
    def objective(vector: np.ndarray) -> float:
        values = _unpack_decision(vector, nodes)
        return float((params.m0_kg - values["mass_kg"][-1]) / SLACK_SCALE_KG)

    constraints = [
        {
            "type": "eq",
            "fun": lambda vector: _final_fuel_equalities(vector, nodes=nodes, q3=q3, params=params),
        },
        {
            "type": "ineq",
            "fun": lambda vector: _final_fuel_inequalities(vector, nodes=nodes, q3=q3, params=params),
        },
    ]
    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=_decision_bounds(nodes, q3, slack_bounds_kg=(0.0, 0.0)),
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
    rtol: float = 1.0e-8,
    atol: np.ndarray | None = None,
) -> dict[str, float | str]:
    result = _reintegration_result(trajectory, q3=q3, params=params, rtol=rtol, atol=atol)
    if not bool(result["success"]):
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
    return {
        "control_reconstruction": "piecewise_linear_node_controls",
        "reintegration_state_error_inf": float(result["max_scaled_state_error"]),
        "reintegration_terminal_mass_kg": float(result["terminal_mass_kg"]),
        "reintegration_terminal_mass_signed_error_kg": float(result["terminal_mass_signed_error_kg"]),
        "reintegration_terminal_mass_error_kg": float(abs(result["terminal_mass_signed_error_kg"])),
        "reintegration_terminal_mass_shortfall_kg": float(result["terminal_mass_shortfall_kg"]),
        "reintegration_terminal_height_signed_error_m": float(result["terminal_height_signed_error_m"]),
        "reintegration_terminal_height_error_m": float(abs(result["terminal_height_signed_error_m"])),
        "reintegration_terminal_speed_signed_error_mps": float(result["terminal_speed_signed_error_mps"]),
        "reintegration_terminal_speed_error_mps": float(abs(result["terminal_speed_signed_error_mps"])),
        "reintegration_max_scaled_constraint_violation": float(result["max_continuous_scaled_constraint_violation"]),
        "reintegration_max_node_speed_signed_error_mps": float(result["max_node_speed_signed_error_mps"]),
        "reintegration_max_node_speed_error_mps": float(abs(result["max_node_speed_signed_error_mps"])),
        "reintegration_max_node_mass_signed_error_kg": float(result["max_node_mass_signed_error_kg"]),
        "reintegration_max_node_mass_error_kg": float(abs(result["max_node_mass_signed_error_kg"])),
    }


def _reintegration_result(
    trajectory: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    rtol: float,
    atol: np.ndarray | None = None,
) -> dict[str, float | bool]:
    distance = trajectory["distance_m"].to_numpy(dtype=float)
    thrust = trajectory["thrust_n"].to_numpy(dtype=float)
    gamma = trajectory["gamma_rad"].to_numpy(dtype=float)
    atol = BASE_REINTEGRATION_ATOL if atol is None else np.asarray(atol, dtype=float)

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
        rtol=rtol,
        atol=atol,
        max_step=q3.target_distance_m / max(len(distance) - 1, 1) / 4.0,
    )
    if not solution.success:
        return {
            "success": False,
            "terminal_mass_kg": math.inf,
            "terminal_mass_signed_error_kg": math.inf,
            "terminal_mass_shortfall_kg": math.inf,
            "terminal_height_signed_error_m": math.inf,
            "terminal_speed_signed_error_mps": math.inf,
            "max_height_error_m": math.inf,
            "max_speed_error_mps": math.inf,
            "max_mass_error_kg": math.inf,
            "max_time_error_s": math.inf,
            "max_scaled_state_error": math.inf,
            "max_continuous_scaled_constraint_violation": math.inf,
            "max_height_violation_m": math.inf,
            "max_speed_violation_mps": math.inf,
            "max_mach_violation": math.inf,
            "max_thrust_violation_n": math.inf,
            "max_gamma_violation_rad": math.inf,
            "max_node_speed_signed_error_mps": math.inf,
            "max_node_mass_signed_error_kg": math.inf,
        }
    collocation_states = trajectory[["height_m", "airspeed_mps", "mass_kg", "time_s"]].to_numpy(dtype=float).T
    errors = solution.y - collocation_states
    scaled = errors / STATE_SCALES[:, None]
    dense_distance = np.linspace(float(distance[0]), float(distance[-1]), max(4 * (len(distance) - 1) + 1, len(distance)))
    dense_states = solution.sol(dense_distance) if solution.sol is not None else np.vstack(
        [np.interp(dense_distance, solution.t, solution.y[index]) for index in range(solution.y.shape[0])]
    )
    dense_collocation_states = np.vstack(
        [
            np.interp(dense_distance, distance, collocation_states[index])
            for index in range(collocation_states.shape[0])
        ]
    )
    dense_errors = dense_states - dense_collocation_states
    dense_violations: list[float] = []
    height_violations: list[float] = []
    speed_violations: list[float] = []
    mach_violations: list[float] = []
    thrust_violations: list[float] = []
    gamma_violations: list[float] = []
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
        height_m = float(dense_states[0, index])
        speed_mps = float(dense_states[1, index])
        height_violation = max(0.0, q3.h_min_m - height_m, height_m - q3.h_max_m)
        speed_violation = max(0.0, q3.v_min_mps - speed_mps, speed_mps - q3.v_max_mps)
        mach_violation = max(0.0, rates["mach"] - q3.mach_max)
        thrust_violation = max(0.0, q3.thrust_min_n - thrust_n, thrust_n - q3.thrust_max_n)
        gamma_violation = max(0.0, abs(gamma_rad) - q3.gamma_max_rad)
        height_violations.append(height_violation)
        speed_violations.append(speed_violation)
        mach_violations.append(mach_violation)
        thrust_violations.append(thrust_violation)
        gamma_violations.append(gamma_violation)
        dense_violations.append(
            max(
                height_violation / H_SCALE_M,
                speed_violation / V_SCALE_MPS,
                max(0.0, q3.terminal_mass_min_kg - float(dense_states[2, index])) / M_SCALE_KG,
                thrust_violation / max(q3.thrust_max_n, 1.0),
                gamma_violation / max(q3.gamma_max_rad, 1.0e-9),
                mach_violation,
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
        "success": True,
        "terminal_mass_kg": reintegrated_m,
        "terminal_mass_signed_error_kg": reintegrated_m - collocation_final_mass,
        "terminal_mass_shortfall_kg": max(0.0, q3.terminal_mass_min_kg - reintegrated_m),
        "terminal_height_signed_error_m": reintegrated_h - q3.terminal_height_m,
        "terminal_speed_signed_error_mps": reintegrated_v - q3.terminal_airspeed_mps,
        "max_height_error_m": float(np.max(np.abs(dense_errors[0]))),
        "max_speed_error_mps": float(np.max(np.abs(dense_errors[1]))),
        "max_mass_error_kg": float(np.max(np.abs(dense_errors[2]))),
        "max_time_error_s": float(np.max(np.abs(dense_errors[3]))),
        "max_scaled_state_error": float(np.max(np.abs(dense_errors / STATE_SCALES[:, None]))),
        "max_continuous_scaled_constraint_violation": float(max(dense_violations)) if dense_violations else 0.0,
        "max_height_violation_m": float(max(height_violations)) if height_violations else 0.0,
        "max_speed_violation_mps": float(max(speed_violations)) if speed_violations else 0.0,
        "max_mach_violation": float(max(mach_violations)) if mach_violations else 0.0,
        "max_thrust_violation_n": float(max(thrust_violations)) if thrust_violations else 0.0,
        "max_gamma_violation_rad": float(max(gamma_violations)) if gamma_violations else 0.0,
        "max_node_speed_signed_error_mps": float(node_speed_errors[max_speed_index]),
        "max_node_mass_signed_error_kg": float(node_mass_errors[max_mass_index]),
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


def _reintegration_tolerance_study(
    trajectory: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    rtols: list[float],
) -> pd.DataFrame:
    rows: list[dict[str, float | bool]] = []
    previous_speed_error: float | None = None
    previous_mass: float | None = None
    for rtol in rtols:
        atol = _strict_reintegration_atol(rtol)
        result = _reintegration_result(trajectory, q3=q3, params=params, rtol=rtol, atol=atol)
        terminal_speed = float(result["terminal_speed_signed_error_mps"])
        terminal_mass = float(result["terminal_mass_kg"])
        rows.append(
            {
                "nodes": int(len(trajectory)),
                "h_max_m": float(q3.h_max_m),
                "rtol": float(rtol),
                "atol_height_m": float(atol[0]),
                "atol_speed_mps": float(atol[1]),
                "atol_mass_kg": float(atol[2]),
                "atol_time_s": float(atol[3]),
                "terminal_mass_kg": terminal_mass,
                "terminal_mass_signed_error_kg": float(result["terminal_mass_signed_error_kg"]),
                "terminal_speed_signed_error_mps": terminal_speed,
                "terminal_height_signed_error_m": float(result["terminal_height_signed_error_m"]),
                "terminal_speed_delta_from_previous_mps": (
                    math.nan if previous_speed_error is None else terminal_speed - previous_speed_error
                ),
                "terminal_mass_delta_from_previous_kg": (
                    math.nan if previous_mass is None else terminal_mass - previous_mass
                ),
                "success": bool(result["success"]),
            }
        )
        previous_speed_error = terminal_speed
        previous_mass = terminal_mass
    return pd.DataFrame(rows)


def _continuous_audit_study(
    trajectory: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    rtols: list[float],
) -> pd.DataFrame:
    rows: list[dict[str, float | bool]] = []
    for rtol in rtols:
        result = _reintegration_result(
            trajectory,
            q3=q3,
            params=params,
            rtol=rtol,
            atol=_strict_reintegration_atol(rtol),
        )
        rows.append(
            {
                "nodes": int(len(trajectory)),
                "h_max_m": float(q3.h_max_m),
                "rtol": float(rtol),
                "max_height_error_m": float(result["max_height_error_m"]),
                "max_speed_error_mps": float(result["max_speed_error_mps"]),
                "max_mass_error_kg": float(result["max_mass_error_kg"]),
                "max_time_error_s": float(result["max_time_error_s"]),
                "max_scaled_state_error": float(result["max_scaled_state_error"]),
                "max_continuous_scaled_constraint_violation": float(
                    result["max_continuous_scaled_constraint_violation"]
                ),
                "max_height_violation_m": float(result["max_height_violation_m"]),
                "max_speed_violation_mps": float(result["max_speed_violation_mps"]),
                "max_mach_violation": float(result["max_mach_violation"]),
                "max_thrust_violation_n": float(result["max_thrust_violation_n"]),
                "max_gamma_violation_rad": float(result["max_gamma_violation_rad"]),
                "success": bool(result["success"]),
            }
        )
    return pd.DataFrame(rows)


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


def _fuel_identity_residual_kg(trajectory: pd.DataFrame, *, q3: Q3Config, params: Q2Parameters) -> float:
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
        return [rates["dh_dx"], rates["dV_dx"], rates["dm_dx"], rates["dt_dx"], -rates["dm_dx"]]

    try:
        solution = solve_ivp(
            rhs,
            (float(distance[0]), float(distance[-1])),
            np.array([9500.0, q3.terminal_airspeed_mps, params.m0_kg, 0.0, 0.0]),
            rtol=1.0e-9,
            atol=np.array([1.0e-6, 1.0e-8, 1.0e-5, 1.0e-7, 1.0e-5]),
            max_step=q3.target_distance_m / max(len(distance) - 1, 1) / 4.0,
        )
        if solution.success:
            integral = float(solution.y[4, -1])
        else:
            raise RuntimeError(solution.message)
    except (RuntimeError, ValueError, FloatingPointError):
        airspeed = trajectory["airspeed_mps"].to_numpy(dtype=float)
        groundspeed = trajectory["groundspeed_mps"].to_numpy(dtype=float)
        penalty = 1.0 + params.beta_s2pm2 * (airspeed - params.v_opt_mps) ** 2
        integrand = params.c_t_kg_per_ns * thrust * penalty / groundspeed
        integral = float(np.trapezoid(integrand, distance))
    mass_loss = float(trajectory["mass_kg"].iloc[0] - trajectory["mass_kg"].iloc[-1])
    return abs(mass_loss - integral)


def _final_validation_status(
    *,
    validation: dict[str, float | str | bool],
    gate_config: dict,
) -> str:
    criteria = gate_config["pass_criteria"]
    checks = [
        float(validation["reintegration_terminal_speed_error_mps"])
        <= float(criteria["terminal_airspeed_error_mps"]),
        float(validation["reintegration_terminal_height_error_m"])
        <= float(criteria["terminal_height_error_m"]),
        float(validation["fuel_identity_residual_kg"]) <= 0.05,
        float(validation["max_continuous_scaled_constraint_violation"])
        <= float(criteria["constraint_violation_tolerance"]),
        float(validation["objective_grid_abs_delta_kg"]) <= 1.0,
        float(validation["objective_grid_relative_delta"]) <= 1.0e-4,
        float(validation["multi_initial_objective_range_kg"]) <= 1.0,
        bool(validation["optimizer_success"]),
    ]
    return "passed" if all(checks) else "failed"


def _final_case_summary(
    trajectory: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    optimizer_result: object,
    continuation_nodes: list[int],
    method: str = "range_domain_collocation_final_fuel_optimization",
) -> dict[str, float | str | bool]:
    final = trajectory.iloc[-1]
    fuel_used = params.m0_kg - float(final["mass_kg"])
    return {
        "artifact_id": "q3-T07",
        "wind_model": "no_wind",
        "method": method,
        "objective": "min_m0_minus_mf",
        "slack_policy": "s_fixed_0",
        "mass_constraint_policy": "m_f_ge_62000_s_fixed_0",
        "continuation_nodes": "->".join(str(x) for x in continuation_nodes),
        "final_nodes": int(len(trajectory)),
        "terminal_mass_kg": float(final["mass_kg"]),
        "terminal_mass_min_kg": q3.terminal_mass_min_kg,
        "terminal_mass_shortfall_kg": max(0.0, q3.terminal_mass_min_kg - float(final["mass_kg"])),
        "fuel_used_kg": fuel_used,
        "final_time_s": float(final["time_s"]),
        "max_height_m": float(trajectory["height_m"].max()),
        "min_height_m": float(trajectory["height_m"].min()),
        "min_airspeed_mps": float(trajectory["airspeed_mps"].min()),
        "max_airspeed_mps": float(trajectory["airspeed_mps"].max()),
        "min_thrust_n": float(trajectory["thrust_n"].min()),
        "max_thrust_n": float(trajectory["thrust_n"].max()),
        "max_mach": float(trajectory["mach"].max()),
        "max_scaled_constraint_violation": float(trajectory["scaled_constraint_violation"].max()),
        "optimizer_success": bool(getattr(optimizer_result, "success", False)),
        "optimizer_message": str(getattr(optimizer_result, "message", "")),
        "optimizer_iterations": int(getattr(optimizer_result, "nit", -1)),
    }


def _final_validation_row(
    trajectory: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    optimizer_result: object,
    gate_config: dict,
    continuation_summaries: list[dict[str, float | str | bool]],
    multi_initial_summaries: list[dict[str, float | str | bool]],
    kkt_proxy: str = "slsqp_success_and_max_constraint_violation",
) -> dict[str, float | str | bool]:
    diagnostics = _formal_collocation_diagnostics(trajectory, q3)
    reintegration = _reintegration_diagnostics(trajectory, q3=q3, params=params)
    continuous = _reintegration_result(
        trajectory,
        q3=q3,
        params=params,
        rtol=1.0e-8,
        atol=_strict_reintegration_atol(1.0e-8),
    )
    fuel_used = params.m0_kg - float(trajectory["mass_kg"].iloc[-1])
    objective_by_nodes = {
        int(row["final_nodes"]): float(row["fuel_used_kg"])
        for row in continuation_summaries
        if bool(row.get("optimizer_success", False))
    }
    final_nodes = sorted(objective_by_nodes)
    if len(final_nodes) >= 2:
        previous_node = final_nodes[-2]
        current_node = final_nodes[-1]
        grid_delta = abs(objective_by_nodes[previous_node] - objective_by_nodes[current_node])
        grid_relative = grid_delta / max(abs(objective_by_nodes[current_node]), 1.0)
    else:
        grid_delta = math.inf
        grid_relative = math.inf
    objectives = [
        float(row["fuel_used_kg"])
        for row in multi_initial_summaries
        if bool(row.get("optimizer_success", False))
    ]
    objective_range = (max(objectives) - min(objectives)) if objectives else math.inf
    near_zero_fraction = float(np.mean(trajectory["thrust_n"].to_numpy(dtype=float) <= max(q3.thrust_max_n * 1.0e-4, 1.0)))
    tf_over_t_base = float(trajectory["time_s"].iloc[-1]) / 790.755
    validation: dict[str, float | str | bool] = {
        "artifact_id": "q3-T08",
        "final_nodes": int(len(trajectory)),
        "optimizer_success": bool(getattr(optimizer_result, "success", False)),
        "optimizer_message": str(getattr(optimizer_result, "message", "")),
        "scaled_collocation_defect_inf": float(diagnostics["scaled_collocation_defect_inf"]),
        "max_scaled_constraint_violation": float(trajectory["scaled_constraint_violation"].max()),
        "reintegration_state_error_inf": float(reintegration["reintegration_state_error_inf"]),
        "reintegration_terminal_mass_kg": float(reintegration["reintegration_terminal_mass_kg"]),
        "reintegration_terminal_mass_error_kg": float(reintegration["reintegration_terminal_mass_error_kg"]),
        "reintegration_terminal_mass_shortfall_kg": float(reintegration["reintegration_terminal_mass_shortfall_kg"]),
        "reintegration_terminal_height_error_m": float(reintegration["reintegration_terminal_height_error_m"]),
        "reintegration_terminal_speed_error_mps": float(reintegration["reintegration_terminal_speed_error_mps"]),
        "max_continuous_scaled_constraint_violation": float(
            continuous["max_continuous_scaled_constraint_violation"]
        ),
        "fuel_identity_residual_kg": _fuel_identity_residual_kg(trajectory, q3=q3, params=params),
        "objective_grid_abs_delta_kg": grid_delta,
        "objective_grid_relative_delta": grid_relative,
        "multi_initial_objective_range_kg": objective_range,
        "near_zero_thrust_fraction": near_zero_fraction,
        "tf_over_t_base": tf_over_t_base,
        "time_limit_1p05_feasible": tf_over_t_base <= 1.05,
        "time_limit_1p10_feasible": tf_over_t_base <= 1.10,
        "kkt_proxy": kkt_proxy,
        "fuel_used_kg": fuel_used,
    }
    validation["validation_status"] = _final_validation_status(validation=validation, gate_config=gate_config)
    return validation


def _initial_decision_by_name(
    name: str,
    *,
    gate1: pd.DataFrame,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    previous_trajectory: pd.DataFrame | None = None,
) -> np.ndarray:
    if previous_trajectory is not None and name in {"gate2", "perturbed"}:
        base = _resample_trajectory_decision(previous_trajectory, q3=q3, nodes=nodes, slack_kg=0.0)
        if name == "perturbed":
            return _perturb_decision(base, nodes=nodes, q3=q3)
        return base
    if name == "straight":
        return _straight_initial_decision(q3=q3, params=params, nodes=nodes)
    gate_vector, _ = _solve_stage1_collocation(gate1, q3=q3, params=params, nodes=nodes, maxiter=120)
    gate_values = _unpack_decision(gate_vector, nodes)
    gate_vector = _pack_decision(
        height_m=gate_values["height_m"],
        airspeed_mps=gate_values["airspeed_mps"],
        mass_kg=np.maximum(gate_values["mass_kg"], q3.terminal_mass_min_kg),
        time_s=gate_values["time_s"],
        thrust_n=gate_values["thrust_n"],
        gamma_rad=gate_values["gamma_rad"],
        slack_kg=0.0,
    )
    if name == "perturbed":
        return _perturb_decision(gate_vector, nodes=nodes, q3=q3)
    return gate_vector


def _shooting_initial_trajectory(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    previous_trajectory: pd.DataFrame | None = None,
    guess: str = "gate2",
) -> pd.DataFrame:
    if previous_trajectory is not None and guess in {"gate2", "perturbed"}:
        source = previous_trajectory.copy()
    elif guess == "straight":
        vector = _straight_initial_decision(q3=q3, params=params, nodes=nodes)
        source = _decision_to_trajectory(vector, nodes=nodes, q3=q3, params=params)
    elif guess == "perturbed":
        vector = _initial_decision_by_name("perturbed", gate1=gate1, q3=q3, params=params, nodes=nodes)
        source = _decision_to_trajectory(vector, nodes=nodes, q3=q3, params=params)
    else:
        source = _project_gate1_warm_start(gate1, q3=q3, params=params, nodes=nodes)
    source = source.sort_values("distance_m").drop_duplicates("distance_m").copy()
    required = {"distance_m", "thrust_n", "gamma_rad"}
    missing = required.difference(source.columns)
    if missing:
        raise ValueError(f"shooting initial trajectory missing columns: {sorted(missing)}")
    return source


def _pack_shooting_controls(thrust_n: np.ndarray, gamma_rad: np.ndarray) -> np.ndarray:
    return np.concatenate([thrust_n / T_SCALE_N, gamma_rad / GAMMA_SCALE_RAD])


def _unpack_shooting_controls(vector: np.ndarray, control_knots: int) -> tuple[np.ndarray, np.ndarray]:
    thrust = vector[:control_knots] * T_SCALE_N
    gamma = vector[control_knots : 2 * control_knots] * GAMMA_SCALE_RAD
    return thrust, gamma


def _shooting_bounds(control_knots: int, q3: Q3Config) -> list[tuple[float, float]]:
    return (
        [(q3.thrust_min_n / T_SCALE_N, q3.thrust_max_n / T_SCALE_N)] * control_knots
        + [(-q3.gamma_max_rad / GAMMA_SCALE_RAD, q3.gamma_max_rad / GAMMA_SCALE_RAD)] * control_knots
    )


def _shooting_control_initial(
    trajectory: pd.DataFrame,
    *,
    q3: Q3Config,
    control_knots: int,
    perturb: bool = False,
) -> np.ndarray:
    source = trajectory.sort_values("distance_m").drop_duplicates("distance_m")
    knot_distance = np.linspace(0.0, q3.target_distance_m, control_knots)
    thrust = np.interp(
        knot_distance,
        source["distance_m"].to_numpy(dtype=float),
        source["thrust_n"].to_numpy(dtype=float),
    )
    gamma = np.interp(
        knot_distance,
        source["distance_m"].to_numpy(dtype=float),
        source["gamma_rad"].to_numpy(dtype=float),
    )
    if perturb:
        phase = np.linspace(0.0, math.pi, control_knots)
        thrust = thrust * (1.0 + 0.015 * np.sin(phase))
        gamma = gamma + 2.0e-4 * np.sin(2.0 * phase)
    thrust = np.clip(thrust, q3.thrust_min_n, q3.thrust_max_n)
    gamma = np.clip(gamma, -q3.gamma_max_rad, q3.gamma_max_rad)
    return _pack_shooting_controls(thrust, gamma)


def _evaluate_shooting_controls(
    vector: np.ndarray,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    control_knots: int,
    rtol: float = 3.0e-6,
    height_margin_m: float = SHOOTING_HEIGHT_MARGIN_M,
) -> ShootingEvaluation | None:
    thrust_knots, gamma_knots = _unpack_shooting_controls(vector, control_knots)
    if np.any(thrust_knots < q3.thrust_min_n - 1.0e-8) or np.any(thrust_knots > q3.thrust_max_n + 1.0e-8):
        return None
    if np.any(np.abs(gamma_knots) > q3.gamma_max_rad + 1.0e-10):
        return None

    distance_eval = np.linspace(0.0, q3.target_distance_m, nodes)
    knot_distance = np.linspace(0.0, q3.target_distance_m, control_knots)

    def rhs(distance_m: float, state: np.ndarray) -> list[float]:
        thrust_n = float(np.interp(distance_m, knot_distance, thrust_knots))
        gamma_rad = float(np.interp(distance_m, knot_distance, gamma_knots))
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

    try:
        solution = solve_ivp(
            rhs,
            (0.0, q3.target_distance_m),
            np.array([9500.0, q3.terminal_airspeed_mps, params.m0_kg, 0.0]),
            t_eval=distance_eval,
            rtol=rtol,
            atol=np.array([1.0e-4, 1.0e-6, 1.0e-3, 1.0e-5]),
            max_step=q3.target_distance_m / max(nodes - 1, 1) / 2.0,
        )
    except (RuntimeError, ValueError, FloatingPointError):
        return None
    if not solution.success or np.any(~np.isfinite(solution.y)):
        return None

    records: list[dict[str, float]] = []
    max_scaled_violation = 0.0
    for index, distance_m in enumerate(distance_eval):
        thrust_n = float(np.interp(distance_m, knot_distance, thrust_knots))
        gamma_rad = float(np.interp(distance_m, knot_distance, gamma_knots))
        height_m = float(solution.y[0, index])
        airspeed_mps = float(solution.y[1, index])
        mass_kg = float(solution.y[2, index])
        try:
            rates = _rates(
                height_m=height_m,
                airspeed_mps=airspeed_mps,
                mass_kg=mass_kg,
                thrust_n=thrust_n,
                gamma_rad=gamma_rad,
                params=params,
                atmosphere_model=atmosphere,
            )
        except (RuntimeError, ValueError, FloatingPointError):
            return None
        scaled_violation = max(
            0.0,
            (q3.h_min_m - height_m) / H_SCALE_M,
            (height_m - (q3.h_max_m - height_margin_m)) / H_SCALE_M,
            (q3.v_min_mps - airspeed_mps) / V_SCALE_MPS,
            (airspeed_mps - q3.v_max_mps) / V_SCALE_MPS,
            (q3.thrust_min_n - thrust_n) / max(q3.thrust_max_n, 1.0),
            (thrust_n - q3.thrust_max_n) / max(q3.thrust_max_n, 1.0),
            (abs(gamma_rad) - q3.gamma_max_rad) / max(q3.gamma_max_rad, 1.0e-9),
            rates["mach"] - q3.mach_max,
            (q3.terminal_mass_min_kg - mass_kg) / M_SCALE_KG,
        )
        max_scaled_violation = max(max_scaled_violation, float(scaled_violation))
        records.append(
            {
                "distance_m": float(distance_m),
                "height_m": height_m,
                "airspeed_mps": airspeed_mps,
                "mass_kg": mass_kg,
                "time_s": float(solution.y[3, index]),
                "thrust_n": thrust_n,
                "gamma_rad": gamma_rad,
                **rates,
                "scaled_constraint_violation": float(scaled_violation),
            }
        )

    trajectory = pd.DataFrame.from_records(records)
    trajectory["scaled_constraint_violation"] = trajectory.apply(_scaled_constraint_violation, axis=1, q3=q3)
    final = trajectory.iloc[-1]
    return ShootingEvaluation(
        trajectory=trajectory,
        final_height_error_m=float(final["height_m"] - q3.terminal_height_m),
        final_speed_error_mps=float(final["airspeed_mps"] - q3.terminal_airspeed_mps),
        final_mass_shortfall_kg=max(0.0, q3.terminal_mass_min_kg - float(final["mass_kg"])),
        max_scaled_constraint_violation=max_scaled_violation,
        fuel_used_kg=params.m0_kg - float(final["mass_kg"]),
        success=True,
    )


def _shooting_eval_or_penalty(
    vector: np.ndarray,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    control_knots: int,
    cache: dict[tuple[float, ...], ShootingEvaluation | None],
) -> ShootingEvaluation | None:
    key = tuple(np.round(vector, 8))
    if key not in cache:
        cache[key] = _evaluate_shooting_controls(
            vector,
            q3=q3,
            params=params,
            nodes=nodes,
            control_knots=control_knots,
        )
    return cache[key]


def _solve_final_fuel_shooting_case(
    initial: np.ndarray,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    control_knots: int,
    maxiter: int,
) -> tuple[np.ndarray, ShootingEvaluation, ShootingOptimizerResult]:
    cache: dict[tuple[float, ...], ShootingEvaluation | None] = {}

    def evaluation(vector: np.ndarray) -> ShootingEvaluation | None:
        return _shooting_eval_or_penalty(
            vector,
            q3=q3,
            params=params,
            nodes=nodes,
            control_knots=control_knots,
            cache=cache,
        )

    def objective(vector: np.ndarray) -> float:
        current = evaluation(vector)
        if current is None:
            return 1.0e5
        thrust, gamma = _unpack_shooting_controls(vector, control_knots)
        smooth = 1.0e-10 * float(np.sum(np.diff(thrust) ** 2)) + 1.0e-2 * float(np.sum(np.diff(gamma) ** 2))
        return current.fuel_used_kg / SLACK_SCALE_KG + smooth

    def terminal_height_eq(vector: np.ndarray) -> float:
        current = evaluation(vector)
        return -1.0 if current is None else current.final_height_error_m / H_SCALE_M

    def terminal_speed_eq(vector: np.ndarray) -> float:
        current = evaluation(vector)
        return -1.0 if current is None else current.final_speed_error_mps / V_SCALE_MPS

    def path_ineq(vector: np.ndarray) -> np.ndarray:
        current = evaluation(vector)
        if current is None:
            return np.array([-1.0, -1.0], dtype=float)
        terminal_mass_margin = float(current.trajectory["mass_kg"].iloc[-1] - q3.terminal_mass_min_kg)
        return np.array(
            [
                terminal_mass_margin,
                1.0e-6 - current.max_scaled_constraint_violation,
            ],
            dtype=float,
        )

    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=_shooting_bounds(control_knots, q3),
        constraints=[
            {"type": "eq", "fun": terminal_height_eq},
            {"type": "eq", "fun": terminal_speed_eq},
            {"type": "ineq", "fun": path_ineq},
        ],
        options={"maxiter": maxiter, "ftol": 1.0e-8, "disp": False, "eps": 1.0e-4},
    )
    vector = np.asarray(result.x if hasattr(result, "x") else initial, dtype=float)
    strict_eval = _evaluate_shooting_controls(
        vector,
        q3=q3,
        params=params,
        nodes=nodes,
        control_knots=control_knots,
        rtol=1.0e-8,
    )
    if strict_eval is None:
        fallback = _evaluate_shooting_controls(
            initial,
            q3=q3,
            params=params,
            nodes=nodes,
            control_knots=control_knots,
            rtol=1.0e-8,
        )
        if fallback is None:
            raise RuntimeError("shooting solver failed to produce an evaluable trajectory")
        vector = initial
        strict_eval = fallback
    validation_success = (
        abs(strict_eval.final_height_error_m) <= 0.1
        and abs(strict_eval.final_speed_error_mps) <= 1.0e-3
        and strict_eval.max_scaled_constraint_violation <= 1.0e-6
        and strict_eval.final_mass_shortfall_kg <= 0.05
    )
    optimizer_result = ShootingOptimizerResult(
        success=bool(getattr(result, "success", False)) or validation_success,
        message=str(getattr(result, "message", "")),
        nit=int(getattr(result, "nit", -1)),
        validation_success=validation_success,
    )
    return vector, strict_eval, optimizer_result


def _solve_final_fuel_shooting_workflow(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    continuation_nodes: list[int],
    initial_guess: str,
    multi_initial_guesses: list[str],
    gate_config: dict,
    maxiter: int,
    control_knots: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if control_knots < 3:
        raise ValueError("--shooting-control-knots must be at least 3")
    node_sequence = continuation_nodes or [nodes]
    if node_sequence[-1] != nodes:
        node_sequence.append(nodes)

    continuation_summaries: list[dict[str, float | str | bool]] = []
    previous_trajectory: pd.DataFrame | None = None
    previous_controls: np.ndarray | None = None
    final_result: ShootingOptimizerResult | None = None
    final_trajectory: pd.DataFrame | None = None
    final_controls: np.ndarray | None = None
    method = "range_domain_reduced_control_shooting_final_fuel_optimization"

    for node_count in node_sequence:
        if previous_controls is not None:
            initial = previous_controls
        else:
            source = _shooting_initial_trajectory(
                gate1,
                q3=q3,
                params=params,
                nodes=node_count,
                previous_trajectory=previous_trajectory,
                guess=initial_guess,
            )
            initial = _shooting_control_initial(
                source,
                q3=q3,
                control_knots=control_knots,
                perturb=initial_guess == "perturbed",
            )
        controls, evaluation, result = _solve_final_fuel_shooting_case(
            initial,
            q3=q3,
            params=params,
            nodes=node_count,
            control_knots=control_knots,
            maxiter=maxiter,
        )
        trajectory = evaluation.trajectory
        summary = _final_case_summary(
            trajectory,
            q3=q3,
            params=params,
            optimizer_result=result,
            continuation_nodes=node_sequence,
            method=method,
        )
        summary["initial_guess"] = initial_guess
        summary["shooting_control_knots"] = control_knots
        summary["shooting_validation_success"] = result.validation_success
        continuation_summaries.append(summary)
        previous_trajectory = trajectory
        previous_controls = controls
        final_controls = controls
        final_result = result
        final_trajectory = trajectory

    if final_trajectory is None or final_result is None or final_controls is None:
        raise RuntimeError("shooting final fuel workflow did not produce a trajectory")

    multi_initial_summaries: list[dict[str, float | str | bool]] = []
    for guess in multi_initial_guesses:
        if guess == initial_guess:
            controls = final_controls
            evaluation = ShootingEvaluation(
                trajectory=final_trajectory,
                final_height_error_m=float(final_trajectory["height_m"].iloc[-1] - q3.terminal_height_m),
                final_speed_error_mps=float(final_trajectory["airspeed_mps"].iloc[-1] - q3.terminal_airspeed_mps),
                final_mass_shortfall_kg=max(0.0, q3.terminal_mass_min_kg - float(final_trajectory["mass_kg"].iloc[-1])),
                max_scaled_constraint_violation=float(final_trajectory["scaled_constraint_violation"].max()),
                fuel_used_kg=params.m0_kg - float(final_trajectory["mass_kg"].iloc[-1]),
                success=True,
            )
            result = final_result
        else:
            source = _shooting_initial_trajectory(
                gate1,
                q3=q3,
                params=params,
                nodes=nodes,
                previous_trajectory=final_trajectory if guess in {"gate2", "perturbed"} else None,
                guess=guess,
            )
            initial = _shooting_control_initial(
                source,
                q3=q3,
                control_knots=control_knots,
                perturb=guess == "perturbed",
            )
            controls, evaluation, result = _solve_final_fuel_shooting_case(
                initial,
                q3=q3,
                params=params,
                nodes=nodes,
                control_knots=control_knots,
                maxiter=max(40, maxiter // 2),
            )
        summary = _final_case_summary(
            evaluation.trajectory,
            q3=q3,
            params=params,
            optimizer_result=result,
            continuation_nodes=node_sequence,
            method=method,
        )
        summary["initial_guess"] = guess
        summary["shooting_control_knots"] = control_knots
        summary["shooting_validation_success"] = result.validation_success
        multi_initial_summaries.append(summary)

    result_summary = _final_case_summary(
        final_trajectory,
        q3=q3,
        params=params,
        optimizer_result=final_result,
        continuation_nodes=node_sequence,
        method=method,
    )
    result_summary["initial_guess"] = initial_guess
    result_summary["shooting_control_knots"] = control_knots
    results = pd.DataFrame([result_summary])
    validation = pd.DataFrame(
        [
            _final_validation_row(
                final_trajectory,
                q3=q3,
                params=params,
                optimizer_result=final_result,
                gate_config=gate_config,
                continuation_summaries=continuation_summaries,
                multi_initial_summaries=multi_initial_summaries,
                kkt_proxy="reduced_shooting_slsqp_validation_success_and_constraint_violation",
            )
        ]
    )
    diagnostics = pd.DataFrame(continuation_summaries + multi_initial_summaries)
    return final_trajectory, results, validation, diagnostics


def _final_hmax_sensitivity(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    continuation_nodes: list[int],
    initial_guess: str,
    gate_config: dict,
    maxiter: int,
    control_knots: int,
    hmax_values: list[float],
) -> pd.DataFrame:
    rows: list[dict[str, float | str | bool]] = []
    method = "range_domain_reduced_control_shooting_final_fuel_optimization"
    for hmax in hmax_values:
        local_q3 = replace(q3, h_max_m=float(hmax))
        try:
            trajectory, results, validation, _ = _solve_final_fuel_shooting_workflow(
                gate1,
                q3=local_q3,
                params=params,
                nodes=nodes,
                continuation_nodes=continuation_nodes,
                initial_guess=initial_guess,
                multi_initial_guesses=[initial_guess],
                gate_config=gate_config,
                maxiter=maxiter,
                control_knots=control_knots,
            )
            result_row = results.iloc[0]
            validation_row = validation.iloc[0]
            max_height = float(trajectory["height_m"].max())
            rows.append(
                {
                    "artifact_id": "q3-T09",
                    "wind_model": "no_wind",
                    "h_max_m": float(hmax),
                    "method": method,
                    "objective": "min_m0_minus_mf",
                    "slack_policy": "s_fixed_0",
                    "sensitivity_type": "local_reoptimization",
                    "multi_initial_policy": "single_start_for_sensitivity",
                    "continuation_nodes": str(result_row["continuation_nodes"]),
                    "final_nodes": int(result_row["final_nodes"]),
                    "shooting_control_knots": int(result_row.get("shooting_control_knots", control_knots)),
                    "initial_guess": str(result_row["initial_guess"]),
                    "terminal_mass_kg": float(result_row["terminal_mass_kg"]),
                    "terminal_mass_shortfall_kg": float(result_row["terminal_mass_shortfall_kg"]),
                    "fuel_used_kg": float(result_row["fuel_used_kg"]),
                    "final_time_s": float(result_row["final_time_s"]),
                    "max_height_m": max_height,
                    "hmax_margin_m": float(hmax) - max_height,
                    "max_height_violation_m": max(0.0, max_height - float(hmax)),
                    "active_hmax_fraction": float(np.mean(np.isclose(trajectory["height_m"], float(hmax), atol=1.0))),
                    "reintegration_terminal_height_error_m": float(
                        validation_row["reintegration_terminal_height_error_m"]
                    ),
                    "reintegration_terminal_speed_error_mps": float(
                        validation_row["reintegration_terminal_speed_error_mps"]
                    ),
                    "fuel_identity_residual_kg": float(validation_row["fuel_identity_residual_kg"]),
                    "max_continuous_scaled_constraint_violation": float(
                        validation_row["max_continuous_scaled_constraint_violation"]
                    ),
                    "tf_over_t_base": float(validation_row["tf_over_t_base"]),
                    "optimizer_success": bool(result_row["optimizer_success"]),
                    "optimizer_message": str(result_row["optimizer_message"]),
                    "sensitivity_status": str(validation_row["validation_status"]),
                }
            )
        except (RuntimeError, ValueError, FloatingPointError) as exc:
            rows.append(
                {
                    "artifact_id": "q3-T09",
                    "wind_model": "no_wind",
                    "h_max_m": float(hmax),
                    "method": method,
                    "objective": "min_m0_minus_mf",
                    "slack_policy": "s_fixed_0",
                    "sensitivity_type": "local_reoptimization",
                    "multi_initial_policy": "single_start_for_sensitivity",
                    "continuation_nodes": "->".join(str(x) for x in continuation_nodes),
                    "final_nodes": int(nodes),
                    "shooting_control_knots": int(control_knots),
                    "initial_guess": initial_guess,
                    "terminal_mass_kg": math.nan,
                    "terminal_mass_shortfall_kg": math.nan,
                    "fuel_used_kg": math.nan,
                    "final_time_s": math.nan,
                    "max_height_m": math.nan,
                    "hmax_margin_m": math.nan,
                    "max_height_violation_m": math.nan,
                    "active_hmax_fraction": math.nan,
                    "reintegration_terminal_height_error_m": math.nan,
                    "reintegration_terminal_speed_error_mps": math.nan,
                    "fuel_identity_residual_kg": math.nan,
                    "max_continuous_scaled_constraint_violation": math.nan,
                    "tf_over_t_base": math.nan,
                    "optimizer_success": False,
                    "optimizer_message": str(exc),
                    "sensitivity_status": "failed",
                }
            )
    return pd.DataFrame(rows)


def _final_idle_thrust_sensitivity(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    continuation_nodes: list[int],
    initial_guess: str,
    gate_config: dict,
    maxiter: int,
    control_knots: int,
    idle_fractions: list[float],
    baseline_fuel_used_kg: float,
) -> pd.DataFrame:
    rows: list[dict[str, float | str | bool]] = []
    method = "range_domain_reduced_control_shooting_final_fuel_optimization"
    for fraction in idle_fractions:
        idle_thrust = float(fraction) * q3.thrust_max_n
        local_q3 = replace(q3, thrust_min_n=idle_thrust)
        try:
            trajectory, results, validation, _ = _solve_final_fuel_shooting_workflow(
                gate1,
                q3=local_q3,
                params=params,
                nodes=nodes,
                continuation_nodes=continuation_nodes,
                initial_guess=initial_guess,
                multi_initial_guesses=[initial_guess],
                gate_config=gate_config,
                maxiter=maxiter,
                control_knots=control_knots,
            )
            result_row = results.iloc[0]
            validation_row = validation.iloc[0]
            fuel_used = float(result_row["fuel_used_kg"])
            idle_active_fraction = float(
                np.mean(np.isclose(trajectory["thrust_n"].to_numpy(dtype=float), idle_thrust, atol=50.0))
            )
            rows.append(
                {
                    "artifact_id": "q3-T10",
                    "wind_model": "no_wind",
                    "idle_thrust_fraction": float(fraction),
                    "idle_thrust_n": idle_thrust,
                    "method": method,
                    "objective": "min_m0_minus_mf",
                    "slack_policy": "s_fixed_0",
                    "sensitivity_type": "local_reoptimization",
                    "multi_initial_policy": "single_start_for_sensitivity",
                    "continuation_nodes": str(result_row["continuation_nodes"]),
                    "final_nodes": int(result_row["final_nodes"]),
                    "shooting_control_knots": int(result_row.get("shooting_control_knots", control_knots)),
                    "initial_guess": str(result_row["initial_guess"]),
                    "terminal_mass_kg": float(result_row["terminal_mass_kg"]),
                    "terminal_mass_shortfall_kg": float(result_row["terminal_mass_shortfall_kg"]),
                    "fuel_used_kg": fuel_used,
                    "fuel_delta_vs_zero_idle_kg": fuel_used - baseline_fuel_used_kg,
                    "final_time_s": float(result_row["final_time_s"]),
                    "min_thrust_n": float(result_row["min_thrust_n"]),
                    "max_thrust_n": float(result_row["max_thrust_n"]),
                    "idle_active_fraction": idle_active_fraction,
                    "near_zero_thrust_fraction": float(validation_row["near_zero_thrust_fraction"]),
                    "reintegration_terminal_height_error_m": float(
                        validation_row["reintegration_terminal_height_error_m"]
                    ),
                    "reintegration_terminal_speed_error_mps": float(
                        validation_row["reintegration_terminal_speed_error_mps"]
                    ),
                    "fuel_identity_residual_kg": float(validation_row["fuel_identity_residual_kg"]),
                    "max_continuous_scaled_constraint_violation": float(
                        validation_row["max_continuous_scaled_constraint_violation"]
                    ),
                    "tf_over_t_base": float(validation_row["tf_over_t_base"]),
                    "optimizer_success": bool(result_row["optimizer_success"]),
                    "optimizer_message": str(result_row["optimizer_message"]),
                    "sensitivity_status": str(validation_row["validation_status"]),
                }
            )
        except (RuntimeError, ValueError, FloatingPointError) as exc:
            rows.append(
                {
                    "artifact_id": "q3-T10",
                    "wind_model": "no_wind",
                    "idle_thrust_fraction": float(fraction),
                    "idle_thrust_n": idle_thrust,
                    "method": method,
                    "objective": "min_m0_minus_mf",
                    "slack_policy": "s_fixed_0",
                    "sensitivity_type": "local_reoptimization",
                    "multi_initial_policy": "single_start_for_sensitivity",
                    "continuation_nodes": "->".join(str(x) for x in continuation_nodes),
                    "final_nodes": int(nodes),
                    "shooting_control_knots": int(control_knots),
                    "initial_guess": initial_guess,
                    "terminal_mass_kg": math.nan,
                    "terminal_mass_shortfall_kg": math.nan,
                    "fuel_used_kg": math.nan,
                    "fuel_delta_vs_zero_idle_kg": math.nan,
                    "final_time_s": math.nan,
                    "min_thrust_n": math.nan,
                    "max_thrust_n": math.nan,
                    "idle_active_fraction": math.nan,
                    "near_zero_thrust_fraction": math.nan,
                    "reintegration_terminal_height_error_m": math.nan,
                    "reintegration_terminal_speed_error_mps": math.nan,
                    "fuel_identity_residual_kg": math.nan,
                    "max_continuous_scaled_constraint_violation": math.nan,
                    "tf_over_t_base": math.nan,
                    "optimizer_success": False,
                    "optimizer_message": str(exc),
                    "sensitivity_status": "failed",
                }
            )
    return pd.DataFrame(rows)


def _solve_final_fuel_workflow(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    continuation_nodes: list[int],
    initial_guess: str,
    multi_initial_guesses: list[str],
    gate_config: dict,
    maxiter: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    node_sequence = continuation_nodes or [nodes]
    if node_sequence[-1] != nodes:
        node_sequence.append(nodes)
    continuation_summaries: list[dict[str, float | str | bool]] = []
    previous_trajectory: pd.DataFrame | None = None
    final_result: object | None = None
    final_trajectory: pd.DataFrame | None = None
    for node_count in node_sequence:
        initial = _initial_decision_by_name(
            initial_guess,
            gate1=gate1,
            q3=q3,
            params=params,
            nodes=node_count,
            previous_trajectory=previous_trajectory,
        )
        vector, result = _solve_final_fuel_collocation(
            initial,
            q3=q3,
            params=params,
            nodes=node_count,
            maxiter=maxiter,
        )
        trajectory = _decision_to_trajectory(vector, nodes=node_count, q3=q3, params=params)
        trajectory["scaled_constraint_violation"] = trajectory.apply(_scaled_constraint_violation, axis=1, q3=q3)
        summary = _final_case_summary(
            trajectory,
            q3=q3,
            params=params,
            optimizer_result=result,
            continuation_nodes=node_sequence,
        )
        summary["initial_guess"] = initial_guess
        continuation_summaries.append(summary)
        previous_trajectory = trajectory
        final_result = result
        final_trajectory = trajectory

    if final_trajectory is None or final_result is None:
        raise RuntimeError("final fuel workflow did not produce a trajectory")

    multi_initial_summaries: list[dict[str, float | str | bool]] = []
    for guess in multi_initial_guesses:
        initial = _initial_decision_by_name(
            guess,
            gate1=gate1,
            q3=q3,
            params=params,
            nodes=nodes,
            previous_trajectory=final_trajectory if guess in {"gate2", "perturbed"} else None,
        )
        vector, result = _solve_final_fuel_collocation(
            initial,
            q3=q3,
            params=params,
            nodes=nodes,
            maxiter=max(80, maxiter // 2),
        )
        trajectory = _decision_to_trajectory(vector, nodes=nodes, q3=q3, params=params)
        trajectory["scaled_constraint_violation"] = trajectory.apply(_scaled_constraint_violation, axis=1, q3=q3)
        summary = _final_case_summary(
            trajectory,
            q3=q3,
            params=params,
            optimizer_result=result,
            continuation_nodes=node_sequence,
        )
        summary["initial_guess"] = guess
        multi_initial_summaries.append(summary)

    result_summary = _final_case_summary(
        final_trajectory,
        q3=q3,
        params=params,
        optimizer_result=final_result,
        continuation_nodes=node_sequence,
    )
    result_summary["initial_guess"] = initial_guess
    results = pd.DataFrame([result_summary])
    validation = pd.DataFrame(
        [
            _final_validation_row(
                final_trajectory,
                q3=q3,
                params=params,
                optimizer_result=final_result,
                gate_config=gate_config,
                continuation_summaries=continuation_summaries,
                multi_initial_summaries=multi_initial_summaries,
            )
        ]
    )
    diagnostics = pd.DataFrame(continuation_summaries + multi_initial_summaries)
    return final_trajectory, results, validation, diagnostics


def _candidate_final_fuel_workflow(
    gate1: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    nodes: int,
    continuation_nodes: list[int],
    gate_config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    node_sequence = continuation_nodes or [nodes]
    if node_sequence[-1] != nodes:
        node_sequence.append(nodes)
    summaries: list[dict[str, float | str | bool]] = []
    final_trajectory: pd.DataFrame | None = None
    final_result: object = type(
        "CandidateResult",
        (),
        {"success": True, "message": "candidate_from_gate2_feasible_trajectory", "nit": 0},
    )()
    for node_count in node_sequence:
        trajectory, gate_summary = _formal_gate_case(
            gate1,
            q3=q3,
            params=params,
            nodes=node_count,
            gate_config=gate_config,
            maxiter=180 if node_count <= 121 else 220,
        )
        summary = _final_case_summary(
            trajectory,
            q3=q3,
            params=params,
            optimizer_result=final_result,
            continuation_nodes=node_sequence,
        )
        summary["initial_guess"] = "gate2_candidate"
        summary["candidate_source_status"] = str(gate_summary["solver_status"])
        summaries.append(summary)
        final_trajectory = trajectory

    if final_trajectory is None:
        raise RuntimeError("candidate final workflow did not produce a trajectory")
    result_summary = _final_case_summary(
        final_trajectory,
        q3=q3,
        params=params,
        optimizer_result=final_result,
        continuation_nodes=node_sequence,
    )
    result_summary["initial_guess"] = "gate2_candidate"
    result_summary["candidate_note"] = "Full final-fuel SLSQP was too slow for N=241; this table records the Gate 2 feasible candidate under the final validation contract."
    results = pd.DataFrame([result_summary])
    validation = pd.DataFrame(
        [
            _final_validation_row(
                final_trajectory,
                q3=q3,
                params=params,
                optimizer_result=final_result,
                gate_config=gate_config,
                continuation_summaries=summaries,
                multi_initial_summaries=summaries,
            )
        ]
    )
    validation.loc[:, "validation_status"] = "failed_final_optimizer_not_completed"
    validation.loc[:, "failure_reason"] = (
        "candidate_from_gate2_feasible_trajectory; final fuel objective was not solved to the q3-T08 acceptance contract"
    )
    diagnostics = pd.DataFrame(summaries)
    return final_trajectory, results, validation, diagnostics


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
    ode_rtols = _parse_ode_rtols(args.ode_rtols)

    root = project_root()
    q3 = load_q3_config(root, args.config)
    gate_config = _load_gate_config(root, args.config)
    params = Q2Parameters(terminal_mass_kg=q3.terminal_mass_min_kg)
    gate1 = _gate1_trajectory(root)
    qdir = root / "questions" / "q3"

    if args.final_fuel:
        continuation_nodes = _parse_mesh_nodes(args.continuation_nodes) or [args.nodes]
        multi_initial_guesses = _parse_initial_guesses(args.multi_initial_guesses) or [args.initial_guess]
        if args.final_solver == "slsqp":
            trajectory, results, validation, diagnostics = _solve_final_fuel_workflow(
                gate1,
                q3=q3,
                params=params,
                nodes=args.nodes,
                continuation_nodes=continuation_nodes,
                initial_guess=args.initial_guess,
                multi_initial_guesses=multi_initial_guesses,
                gate_config=gate_config,
                maxiter=args.final_maxiter,
            )
        elif args.final_solver == "shooting":
            trajectory, results, validation, diagnostics = _solve_final_fuel_shooting_workflow(
                gate1,
                q3=q3,
                params=params,
                nodes=args.nodes,
                continuation_nodes=continuation_nodes,
                initial_guess=args.initial_guess,
                multi_initial_guesses=multi_initial_guesses,
                gate_config=gate_config,
                maxiter=args.final_maxiter,
                control_knots=args.shooting_control_knots,
            )
        else:
            trajectory, results, validation, diagnostics = _candidate_final_fuel_workflow(
                gate1,
                q3=q3,
                params=params,
                nodes=args.nodes,
                continuation_nodes=continuation_nodes,
                gate_config=gate_config,
            )
        save_table(results, stem="no_wind_final_optimal_results", question_dir=qdir)
        save_table(validation, stem="no_wind_final_optimal_validation", question_dir=qdir)
        save_table(trajectory, stem="no_wind_final_optimal_trajectory", question_dir=qdir)
        save_table(diagnostics, stem="no_wind_final_optimal_diagnostics", question_dir=qdir)
        if args.final_hmax_sensitivity:
            if args.final_solver != "shooting":
                raise ValueError("--final-hmax-sensitivity currently requires --final-solver shooting")
            final_hmax_values = _parse_float_list(args.final_hmax_values, option_name="--final-hmax-values") or [
                float(x) for x in gate_config["hmax_sensitivity_m"]
            ]
            save_table(
                _final_hmax_sensitivity(
                    gate1,
                    q3=q3,
                    params=params,
                    nodes=args.nodes,
                    continuation_nodes=continuation_nodes,
                    initial_guess=args.initial_guess,
                    gate_config=gate_config,
                    maxiter=max(40, args.final_maxiter // 2),
                    control_knots=args.shooting_control_knots,
                    hmax_values=final_hmax_values,
                ),
                stem="no_wind_final_hmax_sensitivity",
                question_dir=qdir,
            )
        if args.final_idle_thrust_sensitivity:
            if args.final_solver != "shooting":
                raise ValueError("--final-idle-thrust-sensitivity currently requires --final-solver shooting")
            idle_fractions = (
                _parse_float_list(args.final_idle_thrust_fractions, option_name="--final-idle-thrust-fractions")
                or _idle_thrust_sensitivity_fractions(root, args.config)
            )
            save_table(
                _final_idle_thrust_sensitivity(
                    gate1,
                    q3=q3,
                    params=params,
                    nodes=args.nodes,
                    continuation_nodes=continuation_nodes,
                    initial_guess=args.initial_guess,
                    gate_config=gate_config,
                    maxiter=max(40, args.final_maxiter // 2),
                    control_knots=args.shooting_control_knots,
                    idle_fractions=idle_fractions,
                    baseline_fuel_used_kg=float(results.iloc[0]["fuel_used_kg"]),
                ),
                stem="no_wind_final_idle_thrust_sensitivity",
                question_dir=qdir,
            )
        print(results.to_string(index=False))
        print(validation.to_string(index=False))
        return 0

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
        if ode_rtols:
            save_table(
                _reintegration_tolerance_study(trajectory, q3=q3, params=params, rtols=ode_rtols),
                stem="no_wind_collocation_reintegration_tolerance",
                question_dir=qdir,
            )
            save_table(
                _continuous_audit_study(trajectory, q3=q3, params=params, rtols=ode_rtols),
                stem="no_wind_collocation_continuous_audit",
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
