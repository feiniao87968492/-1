#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
Q2_SCRIPTS = ROOT / "questions" / "q2" / "scripts"
Q3_SCRIPTS = ROOT / "questions" / "q3" / "scripts"
for search_path in [SRC, Q2_SCRIPTS, Q3_SCRIPTS]:
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from fuel_path_model import Q2Parameters, atmosphere, wind_speed_mps  # noqa: E402
from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402
from solve_feasibility_no_wind import Q3Config, load_q3_config  # noqa: E402

H_SCALE_M = 1000.0
V_SCALE_MPS = 100.0
M_SCALE_KG = 10_000.0
T_SCALE_N = 90_000.0


@dataclass(frozen=True)
class WindEvaluation:
    trajectory: pd.DataFrame
    terminal_height_error_m: float
    terminal_speed_error_mps: float
    terminal_mass_shortfall_kg: float
    max_scaled_constraint_violation: float
    fuel_used_kg: float
    final_time_s: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q4 wind-aware integrated cruise strategy pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--nodes", type=int, default=121)
    parser.add_argument("--control-knots", type=int, default=9)
    parser.add_argument("--maxiter", type=int, default=120)
    parser.add_argument("--beta-factors", default="0.8,0.9,1.0,1.1,1.2")
    parser.add_argument("--range-factors", default="1.0,1.03,1.06")
    parser.add_argument("--sensitivity-maxiter", type=int, default=80)
    parser.add_argument("--range-maxiter", type=int, default=80)
    parser.add_argument("--skip-beta-sensitivity", action="store_true")
    parser.add_argument("--skip-range-extension", action="store_true")
    parser.add_argument("--skip-extension-frameworks", action="store_true")
    return parser.parse_args()


def _parse_float_list(raw: str, *, option_name: str) -> list[float]:
    values: list[float] = []
    for part in raw.split(","):
        text = part.strip()
        if not text:
            continue
        try:
            values.append(float(text))
        except ValueError as exc:
            raise ValueError(f"{option_name} contains a non-numeric value: {text}") from exc
    if not values:
        raise ValueError(f"{option_name} must contain at least one value")
    return values


def _load_no_wind_trajectory(root: Path) -> pd.DataFrame:
    path = root / "questions" / "q3" / "artifacts" / "tables" / "no_wind_final_optimal_trajectory.csv"
    if not path.exists():
        raise FileNotFoundError(
            "q4-T02 requires questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv"
        )
    frame = pd.read_csv(path).sort_values("distance_m").drop_duplicates("distance_m")
    required = {"distance_m", "height_m", "airspeed_mps", "mass_kg", "thrust_n", "gamma_rad"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"q3 no-wind trajectory missing required columns: {sorted(missing)}")
    return frame


def _load_q2_standard_baseline(root: Path) -> pd.Series:
    path = root / "artifacts" / "q2" / "data" / "q2_fuel_summary.csv"
    if not path.exists():
        raise FileNotFoundError("q4-T03 requires artifacts/q2/data/q2_fuel_summary.csv")
    summary = pd.read_csv(path)
    row = summary.loc[summary["scenario"] == "standard_isa"]
    if row.empty:
        raise ValueError("q2 fuel summary does not contain scenario=standard_isa")
    return row.iloc[0]


def _load_q1_constant_speed_summary(root: Path) -> pd.Series:
    path = root / "artifacts" / "q1" / "data" / "strategy_comparison.csv"
    if not path.exists():
        raise FileNotFoundError("q4-T03 requires artifacts/q1/data/strategy_comparison.csv")
    summary = pd.read_csv(path)
    row = summary.loc[summary["strategy"] == "constant_speed"]
    if row.empty:
        raise ValueError("q1 strategy comparison does not contain constant_speed")
    return row.iloc[0]


def _load_q1_constant_speed_profile(root: Path) -> pd.DataFrame:
    path = root / "artifacts" / "q1" / "data" / "constant_speed_profile.csv"
    if not path.exists():
        raise FileNotFoundError("q4-T06 requires artifacts/q1/data/constant_speed_profile.csv")
    profile = pd.read_csv(path).sort_values("distance_m").drop_duplicates("distance_m")
    required = {"distance_m", "height_m", "airspeed_mps"}
    missing = required.difference(profile.columns)
    if missing:
        raise ValueError(f"q1 constant-speed profile missing required columns: {sorted(missing)}")
    return profile


def _interp(frame: pd.DataFrame, column: str, distance_m: np.ndarray | float) -> np.ndarray:
    return np.interp(distance_m, frame["distance_m"].to_numpy(dtype=float), frame[column].to_numpy(dtype=float))


def _height_from_q1_profile(profile: pd.DataFrame, distance_m: float) -> float:
    return float(np.interp(distance_m, profile["distance_m"].to_numpy(dtype=float), profile["height_m"].to_numpy(dtype=float)))


def _solve_gamma_for_wind_path_slope(airspeed_mps: float, wind_mps: float, dh_dx: float) -> float:
    gamma = math.atan(dh_dx)
    for _ in range(12):
        denominator = airspeed_mps * math.cos(gamma) + wind_mps
        value = airspeed_mps * math.sin(gamma) / denominator - dh_dx
        derivative = (
            airspeed_mps
            * (airspeed_mps + wind_mps * math.cos(gamma))
            / max(denominator * denominator, 1.0e-12)
        )
        gamma -= value / max(derivative, 1.0e-12)
    return gamma


def _initial_controls_from_no_wind(
    source: pd.DataFrame,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    control_knots: int,
) -> np.ndarray:
    distances = np.linspace(0.0, q3.target_distance_m, control_knots)
    source_distance = source["distance_m"].to_numpy(dtype=float)
    height = _interp(source, "height_m", distances)
    airspeed = _interp(source, "airspeed_mps", distances)
    mass = _interp(source, "mass_kg", distances)
    dh_dx = np.gradient(source["height_m"].to_numpy(dtype=float), source_distance)
    dV_dx = np.gradient(source["airspeed_mps"].to_numpy(dtype=float), source_distance)
    source_dh_dx = np.interp(distances, source_distance, dh_dx)
    source_dv_dx = np.interp(distances, source_distance, dV_dx)

    thrust = np.zeros(control_knots)
    gamma = np.zeros(control_knots)
    for index in range(control_knots):
        gamma[index] = _solve_gamma_for_wind_path_slope(
            float(airspeed[index]),
            wind_speed_mps(float(height[index])),
            float(source_dh_dx[index]),
        )
        rates = _rates(
            mass_kg=float(mass[index]),
            height_m=float(height[index]),
            airspeed_mps=float(airspeed[index]),
            thrust_n=float(_interp(source, "thrust_n", distances[index])),
            gamma_rad=float(gamma[index]),
            params=params,
            q3=q3,
        )
        thrust[index] = (
            float(mass[index])
            * (rates["groundspeed_mps"] * float(source_dv_dx[index]) + params.g_mps2 * math.sin(float(gamma[index])))
            + rates["drag_n"]
        )
    thrust = np.clip(thrust, q3.thrust_min_n + 1.0, q3.thrust_max_n - 1.0)
    gamma = np.clip(gamma, -q3.gamma_max_rad + 1.0e-5, q3.gamma_max_rad - 1.0e-5)
    return _pack_controls(thrust, gamma)


def _pack_controls(thrust_n: np.ndarray, gamma_rad: np.ndarray) -> np.ndarray:
    return np.concatenate([thrust_n / T_SCALE_N, gamma_rad / max(1.0e-9, 0.05236)])


def _unpack_controls(vector: np.ndarray, control_knots: int) -> tuple[np.ndarray, np.ndarray]:
    thrust = vector[:control_knots] * T_SCALE_N
    gamma = vector[control_knots:] * 0.05236
    return thrust, gamma


def _control_bounds(control_knots: int, q3: Q3Config) -> list[tuple[float, float]]:
    thrust_bounds = [(q3.thrust_min_n / T_SCALE_N, q3.thrust_max_n / T_SCALE_N)] * control_knots
    gamma_bounds = [(-q3.gamma_max_rad / 0.05236, q3.gamma_max_rad / 0.05236)] * control_knots
    return thrust_bounds + gamma_bounds


def _rates(
    *,
    mass_kg: float,
    height_m: float,
    airspeed_mps: float,
    thrust_n: float,
    gamma_rad: float,
    params: Q2Parameters,
    q3: Q3Config,
) -> dict[str, float]:
    temperature_k, density_kgm3, sound_speed_mps, pressure_pa = atmosphere(height_m)
    lift_factor = max(math.cos(gamma_rad), 0.0)
    cl = (
        2.0
        * mass_kg
        * params.g_mps2
        * lift_factor
        / (density_kgm3 * airspeed_mps**2 * params.wing_area_m2)
    )
    cd = params.cd0 + params.induced_k * cl**2
    drag_n = 0.5 * density_kgm3 * airspeed_mps**2 * params.wing_area_m2 * cd
    wind_mps = wind_speed_mps(height_m)
    groundspeed_mps = airspeed_mps * math.cos(gamma_rad) + wind_mps
    if groundspeed_mps <= 0.0:
        raise ValueError("non-positive configured-wind ground speed")
    fuel_penalty = 1.0 + params.beta_s2pm2 * (airspeed_mps - params.v_opt_mps) ** 2
    mach = airspeed_mps / sound_speed_mps
    dh_dx = airspeed_mps * math.sin(gamma_rad) / groundspeed_mps
    dV_dx = ((thrust_n - drag_n) / mass_kg - params.g_mps2 * math.sin(gamma_rad)) / groundspeed_mps
    dm_dx = -params.c_t_kg_per_ns * thrust_n * fuel_penalty / groundspeed_mps
    dt_dx = 1.0 / groundspeed_mps
    violation = max(
        (q3.h_min_m - height_m) / H_SCALE_M,
        (height_m - q3.h_max_m) / H_SCALE_M,
        (q3.v_min_mps - airspeed_mps) / V_SCALE_MPS,
        (airspeed_mps - q3.v_max_mps) / V_SCALE_MPS,
        mach - q3.mach_max,
        (q3.thrust_min_n - thrust_n) / T_SCALE_N,
        (thrust_n - q3.thrust_max_n) / T_SCALE_N,
        abs(gamma_rad) - q3.gamma_max_rad,
        (q3.terminal_mass_min_kg - mass_kg) / M_SCALE_KG,
        0.0,
    )
    return {
        "temperature_k": temperature_k,
        "density_kgm3": density_kgm3,
        "sound_speed_mps": sound_speed_mps,
        "pressure_pa": pressure_pa,
        "wind_mps": wind_mps,
        "groundspeed_mps": groundspeed_mps,
        "mach": mach,
        "cl": cl,
        "cd": cd,
        "drag_n": drag_n,
        "dh_dx": dh_dx,
        "dV_dx": dV_dx,
        "dm_dx": dm_dx,
        "dt_dx": dt_dx,
        "fuel_per_meter_kgpm": -dm_dx,
        "scaled_constraint_violation": violation,
    }


def _evaluate_controls(
    vector: np.ndarray,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    control_knots: int,
    nodes: int,
) -> WindEvaluation:
    thrust_knots, gamma_knots = _unpack_controls(vector, control_knots)
    control_distance = np.linspace(0.0, q3.target_distance_m, control_knots)
    output_distance = np.linspace(0.0, q3.target_distance_m, nodes)

    def controls(distance_m: float) -> tuple[float, float]:
        return (
            float(np.interp(distance_m, control_distance, thrust_knots)),
            float(np.interp(distance_m, control_distance, gamma_knots)),
        )

    def rhs(distance_m: float, state: np.ndarray) -> list[float]:
        thrust_n, gamma_rad = controls(distance_m)
        rates = _rates(
            mass_kg=float(state[2]),
            height_m=float(state[0]),
            airspeed_mps=float(state[1]),
            thrust_n=thrust_n,
            gamma_rad=gamma_rad,
            params=params,
            q3=q3,
        )
        return [rates["dh_dx"], rates["dV_dx"], rates["dm_dx"], rates["dt_dx"]]

    solution = solve_ivp(
        rhs,
        (0.0, q3.target_distance_m),
        np.array([params.h0_m, params.v0_mps, params.m0_kg, 0.0]),
        t_eval=output_distance,
        rtol=1.0e-8,
        atol=np.array([1.0e-5, 1.0e-7, 1.0e-4, 1.0e-6]),
        max_step=q3.target_distance_m / max(nodes - 1, 1),
    )
    if not solution.success:
        raise RuntimeError(solution.message)

    records: list[dict[str, float]] = []
    max_violation = 0.0
    for index, distance_m in enumerate(output_distance):
        thrust_n, gamma_rad = controls(float(distance_m))
        height_m = float(solution.y[0, index])
        airspeed_mps = float(solution.y[1, index])
        mass_kg = float(solution.y[2, index])
        rates = _rates(
            mass_kg=mass_kg,
            height_m=height_m,
            airspeed_mps=airspeed_mps,
            thrust_n=thrust_n,
            gamma_rad=gamma_rad,
            params=params,
            q3=q3,
        )
        max_violation = max(max_violation, rates["scaled_constraint_violation"])
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
            }
        )
    trajectory = pd.DataFrame.from_records(records)
    final = trajectory.iloc[-1]
    return WindEvaluation(
        trajectory=trajectory,
        terminal_height_error_m=float(final["height_m"] - q3.terminal_height_m),
        terminal_speed_error_mps=float(final["airspeed_mps"] - q3.terminal_airspeed_mps),
        terminal_mass_shortfall_kg=max(0.0, q3.terminal_mass_min_kg - float(final["mass_kg"])),
        max_scaled_constraint_violation=max_violation,
        fuel_used_kg=params.m0_kg - float(final["mass_kg"]),
        final_time_s=float(final["time_s"]),
    )


def _evaluate_or_none(
    vector: np.ndarray,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    control_knots: int,
    nodes: int,
) -> WindEvaluation | None:
    try:
        return _evaluate_controls(vector, q3=q3, params=params, control_knots=control_knots, nodes=nodes)
    except (RuntimeError, ValueError, FloatingPointError):
        return None


def _fuel_identity_residual(trajectory: pd.DataFrame, params: Q2Parameters) -> float:
    fuel_integral = float(np.trapezoid(trajectory["fuel_per_meter_kgpm"], trajectory["distance_m"]))
    mass_loss = params.m0_kg - float(trajectory["mass_kg"].iloc[-1])
    return abs(mass_loss - fuel_integral)


def _validation_status(
    evaluation: WindEvaluation,
    *,
    fuel_identity_residual_kg: float,
    optimizer_success: bool,
) -> str:
    checks = [
        abs(evaluation.terminal_height_error_m) <= 0.1,
        abs(evaluation.terminal_speed_error_mps) <= 1.0e-3,
        evaluation.terminal_mass_shortfall_kg <= 0.05,
        evaluation.max_scaled_constraint_violation <= 1.0e-6,
        fuel_identity_residual_kg <= 0.1,
    ]
    return "passed" if all(checks) else "failed"


def _solve_wind_optimal(
    *,
    q3: Q3Config,
    params: Q2Parameters,
    source: pd.DataFrame,
    nodes: int,
    control_knots: int,
    maxiter: int,
    initial_vector: np.ndarray | None = None,
) -> tuple[WindEvaluation, object, np.ndarray]:
    initial = (
        np.asarray(initial_vector, dtype=float)
        if initial_vector is not None
        else _initial_controls_from_no_wind(source, q3=q3, params=params, control_knots=control_knots)
    )
    cache: dict[tuple[float, ...], WindEvaluation | None] = {}

    def evaluation(vector: np.ndarray) -> WindEvaluation | None:
        key = tuple(np.round(vector, 10))
        if key not in cache:
            cache[key] = _evaluate_or_none(vector, q3=q3, params=params, control_knots=control_knots, nodes=nodes)
        return cache[key]

    def objective(vector: np.ndarray) -> float:
        current = evaluation(vector)
        if current is None:
            return 1.0e6
        thrust, gamma = _unpack_controls(vector, control_knots)
        smooth = 1.0e-7 * float(np.sum(np.diff(thrust) ** 2)) + 1.0e-2 * float(np.sum(np.diff(gamma) ** 2))
        return current.fuel_used_kg / 1000.0 + smooth

    def terminal_height_eq(vector: np.ndarray) -> float:
        current = evaluation(vector)
        return -1.0 if current is None else current.terminal_height_error_m / H_SCALE_M

    def terminal_speed_eq(vector: np.ndarray) -> float:
        current = evaluation(vector)
        return -1.0 if current is None else current.terminal_speed_error_mps / V_SCALE_MPS

    def path_ineq(vector: np.ndarray) -> np.ndarray:
        current = evaluation(vector)
        if current is None:
            return np.array([-1.0, -1.0])
        return np.array(
            [
                (params.m0_kg - current.fuel_used_kg - q3.terminal_mass_min_kg) / M_SCALE_KG,
                -current.max_scaled_constraint_violation,
            ]
        )

    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=_control_bounds(control_knots, q3),
        constraints=[
            {"type": "eq", "fun": terminal_height_eq},
            {"type": "eq", "fun": terminal_speed_eq},
            {"type": "ineq", "fun": path_ineq},
        ],
        options={"maxiter": maxiter, "ftol": 1.0e-9, "disp": False},
    )
    final_vector = np.asarray(result.x if result.x is not None else initial, dtype=float)
    final = _evaluate_controls(final_vector, q3=q3, params=params, control_knots=control_knots, nodes=nodes)
    return final, result, final_vector


def _params_for_beta(*, q3: Q3Config, beta_s2pm2: float) -> Q2Parameters:
    return Q2Parameters(terminal_mass_kg=q3.terminal_mass_min_kg, beta_s2pm2=beta_s2pm2)


def _wind_result_row(
    evaluation: WindEvaluation,
    *,
    q3: Q3Config,
    params: Q2Parameters,
    optimizer_result: object,
    continuation_nodes: str,
    control_knots: int,
    fuel_identity_residual_kg: float,
) -> pd.DataFrame:
    trajectory = evaluation.trajectory
    optimizer_success = bool(getattr(optimizer_result, "success", False))
    final_mass = params.m0_kg - evaluation.fuel_used_kg
    row = {
        "artifact_id": "q4-T02",
        "wind_model": "configured_wind",
        "method": "range_domain_reduced_control_shooting_wind_optimization",
        "objective": "min_m0_minus_mf",
        "claim_level": "locally_optimized_solution",
        "mass_constraint_policy": "m_f_ge_62000",
        "continuation_nodes": continuation_nodes,
        "final_nodes": int(len(trajectory)),
        "shooting_control_knots": int(control_knots),
        "target_distance_m": q3.target_distance_m,
        "terminal_mass_kg": final_mass,
        "terminal_mass_min_kg": q3.terminal_mass_min_kg,
        "terminal_mass_shortfall_kg": evaluation.terminal_mass_shortfall_kg,
        "fuel_used_kg": evaluation.fuel_used_kg,
        "final_time_s": evaluation.final_time_s,
        "terminal_height_m": float(trajectory["height_m"].iloc[-1]),
        "terminal_height_error_signed_m": evaluation.terminal_height_error_m,
        "terminal_height_error_m": abs(evaluation.terminal_height_error_m),
        "terminal_airspeed_mps": float(trajectory["airspeed_mps"].iloc[-1]),
        "terminal_speed_error_signed_mps": evaluation.terminal_speed_error_mps,
        "terminal_speed_error_mps": abs(evaluation.terminal_speed_error_mps),
        "max_height_m": float(trajectory["height_m"].max()),
        "min_height_m": float(trajectory["height_m"].min()),
        "min_airspeed_mps": float(trajectory["airspeed_mps"].min()),
        "max_airspeed_mps": float(trajectory["airspeed_mps"].max()),
        "min_thrust_n": float(trajectory["thrust_n"].min()),
        "max_thrust_n": float(trajectory["thrust_n"].max()),
        "max_mach": float(trajectory["mach"].max()),
        "max_scaled_constraint_violation": evaluation.max_scaled_constraint_violation,
        "fuel_identity_residual_kg": fuel_identity_residual_kg,
        "near_zero_thrust_fraction": float((trajectory["thrust_n"] <= 1.0e-3 * q3.thrust_max_n).mean()),
        "optimizer_success": optimizer_success,
        "optimizer_message": str(getattr(optimizer_result, "message", "")),
        "optimizer_iterations": int(getattr(optimizer_result, "nit", -1)),
    }
    row["validation_status"] = _validation_status(
        evaluation,
        fuel_identity_residual_kg=fuel_identity_residual_kg,
        optimizer_success=optimizer_success,
    )
    return pd.DataFrame([row])


def _strategy_comparison(
    *,
    q2_baseline: pd.Series,
    q1_constant_speed: pd.Series,
    wind_results: pd.DataFrame,
) -> pd.DataFrame:
    optimal = wind_results.iloc[0]
    fixed_range = float(q2_baseline["final_distance_m"])
    q1_full_range = float(q1_constant_speed["final_distance_m"])
    baseline_fuel = float(q2_baseline["fuel_used_kg"])
    optimal_fuel = float(optimal["fuel_used_kg"])
    fuel_saving = baseline_fuel - optimal_fuel
    common = {
        "artifact_id": "q4-T03",
        "fixed_range_m": fixed_range,
        "q1_constant_speed_full_range_m": q1_full_range,
        "range_change_vs_q1_constant_speed_m": fixed_range - q1_full_range,
    }
    return pd.DataFrame(
        [
            {
                **common,
                "strategy": "constant_speed_baseline",
                "source": "artifacts/q2/data/q2_fuel_summary.csv:standard_isa",
                "fuel_used_kg": baseline_fuel,
                "terminal_mass_kg": float(q2_baseline["final_mass_kg"]),
                "final_time_s": float(q2_baseline["final_time_s"]),
                "fuel_saving_vs_baseline_kg": 0.0,
                "fuel_saving_vs_baseline_pct": 0.0,
                "comparison_status": "baseline",
            },
            {
                **common,
                "strategy": "configured_wind_optimal",
                "source": "questions/q4/artifacts/tables/wind_optimal_results.csv",
                "fuel_used_kg": optimal_fuel,
                "terminal_mass_kg": float(optimal["terminal_mass_kg"]),
                "final_time_s": float(optimal["final_time_s"]),
                "fuel_saving_vs_baseline_kg": fuel_saving,
                "fuel_saving_vs_baseline_pct": 100.0 * fuel_saving / baseline_fuel,
                "comparison_status": str(optimal["validation_status"]),
            },
        ]
    )


def _beta_sensitivity(
    *,
    q3: Q3Config,
    nominal_params: Q2Parameters,
    source: pd.DataFrame,
    nominal_evaluation: WindEvaluation,
    nominal_optimizer_result: object,
    nominal_vector: np.ndarray,
    nodes: int,
    control_knots: int,
    maxiter: int,
    beta_factors: list[float],
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str | bool]] = []
    nominal_beta = nominal_params.beta_s2pm2
    nominal_fuel = nominal_evaluation.fuel_used_kg

    for factor in beta_factors:
        beta_value = nominal_beta * factor
        params = _params_for_beta(q3=q3, beta_s2pm2=beta_value)
        if abs(factor - 1.0) <= 1.0e-12:
            evaluation = nominal_evaluation
            optimizer_result = nominal_optimizer_result
            final_vector = nominal_vector
        else:
            evaluation, optimizer_result, final_vector = _solve_wind_optimal(
                q3=q3,
                params=params,
                source=source,
                nodes=nodes,
                control_knots=control_knots,
                maxiter=maxiter,
                initial_vector=nominal_vector,
            )
        validation_evaluation = _evaluate_controls(
            final_vector,
            q3=q3,
            params=params,
            control_knots=control_knots,
            nodes=max(181, nodes * 3),
        )
        fuel_identity_residual = _fuel_identity_residual(validation_evaluation.trajectory, params)
        optimizer_success = bool(getattr(optimizer_result, "success", False))
        validation_status = _validation_status(
            evaluation,
            fuel_identity_residual_kg=fuel_identity_residual,
            optimizer_success=optimizer_success,
        )
        rows.append(
            {
                "artifact_id": "q4-T04",
                "parameter": "beta_s2pm2",
                "beta_factor": factor,
                "beta_s2pm2": beta_value,
                "nominal_beta_s2pm2": nominal_beta,
                "perturbation_pct": 100.0 * (factor - 1.0),
                "reoptimization_performed": True,
                "post_solution_metric_only": False,
                "claim_level": "local_reoptimization_sensitivity",
                "fuel_used_kg": evaluation.fuel_used_kg,
                "fuel_delta_vs_nominal_kg": evaluation.fuel_used_kg - nominal_fuel,
                "fuel_delta_vs_nominal_pct": 100.0 * (evaluation.fuel_used_kg - nominal_fuel) / nominal_fuel,
                "terminal_mass_kg": params.m0_kg - evaluation.fuel_used_kg,
                "final_time_s": evaluation.final_time_s,
                "terminal_height_error_m": abs(evaluation.terminal_height_error_m),
                "terminal_speed_error_mps": abs(evaluation.terminal_speed_error_mps),
                "max_scaled_constraint_violation": evaluation.max_scaled_constraint_violation,
                "fuel_identity_residual_kg": fuel_identity_residual,
                "near_zero_thrust_fraction": float(
                    (evaluation.trajectory["thrust_n"] <= 1.0e-3 * q3.thrust_max_n).mean()
                ),
                "max_height_m": float(evaluation.trajectory["height_m"].max()),
                "min_airspeed_mps": float(evaluation.trajectory["airspeed_mps"].min()),
                "optimizer_success": optimizer_success,
                "optimizer_iterations": int(getattr(optimizer_result, "nit", -1)),
                "optimizer_message": str(getattr(optimizer_result, "message", "")),
                "validation_status": validation_status,
            }
        )
    return pd.DataFrame(rows).sort_values("beta_factor").reset_index(drop=True)


def _range_extension(
    *,
    q3: Q3Config,
    params: Q2Parameters,
    source: pd.DataFrame,
    q1_profile: pd.DataFrame,
    nominal_evaluation: WindEvaluation,
    nominal_optimizer_result: object,
    nominal_vector: np.ndarray,
    nodes: int,
    control_knots: int,
    maxiter: int,
    range_factors: list[float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, float | int | str | bool]] = []
    fixed_fuel_kg = params.m0_kg - q3.terminal_mass_min_kg
    for factor in range_factors:
        target_distance = q3.target_distance_m * factor
        trial_q3 = replace(
            q3,
            target_distance_m=target_distance,
            terminal_height_m=_height_from_q1_profile(q1_profile, target_distance),
        )
        if abs(factor - 1.0) <= 1.0e-12:
            evaluation = nominal_evaluation
            optimizer_result = nominal_optimizer_result
            final_vector = nominal_vector
        else:
            evaluation, optimizer_result, final_vector = _solve_wind_optimal(
                q3=trial_q3,
                params=params,
                source=source,
                nodes=nodes,
                control_knots=control_knots,
                maxiter=maxiter,
                initial_vector=nominal_vector,
            )
        validation_evaluation = _evaluate_controls(
            final_vector,
            q3=trial_q3,
            params=params,
            control_knots=control_knots,
            nodes=max(181, nodes * 3),
        )
        fuel_identity_residual = _fuel_identity_residual(validation_evaluation.trajectory, params)
        optimizer_success = bool(getattr(optimizer_result, "success", False))
        validation_status = _validation_status(
            evaluation,
            fuel_identity_residual_kg=fuel_identity_residual,
            optimizer_success=optimizer_success,
        )
        rows.append(
            {
                "artifact_id": "q4-T06-trial",
                "range_factor": factor,
                "target_distance_m": target_distance,
                "terminal_height_target_m": trial_q3.terminal_height_m,
                "fuel_budget_kg": fixed_fuel_kg,
                "fuel_used_kg": evaluation.fuel_used_kg,
                "fuel_margin_kg": fixed_fuel_kg - evaluation.fuel_used_kg,
                "terminal_mass_kg": params.m0_kg - evaluation.fuel_used_kg,
                "final_time_s": evaluation.final_time_s,
                "terminal_height_error_m": abs(evaluation.terminal_height_error_m),
                "terminal_speed_error_mps": abs(evaluation.terminal_speed_error_mps),
                "max_scaled_constraint_violation": evaluation.max_scaled_constraint_violation,
                "fuel_identity_residual_kg": fuel_identity_residual,
                "optimizer_success": optimizer_success,
                "optimizer_iterations": int(getattr(optimizer_result, "nit", -1)),
                "optimizer_message": str(getattr(optimizer_result, "message", "")),
                "validation_status": validation_status,
                "feasible_under_fuel_budget": bool(
                    validation_status == "passed" and evaluation.fuel_used_kg <= fixed_fuel_kg + 0.05
                ),
            }
        )
    trials = pd.DataFrame(rows).sort_values("target_distance_m").reset_index(drop=True)

    fuel = trials["fuel_used_kg"].to_numpy(dtype=float)
    distance = trials["target_distance_m"].to_numpy(dtype=float)
    feasible = trials.loc[trials["feasible_under_fuel_budget"]]
    if np.any(fuel >= fixed_fuel_kg) and np.any(fuel <= fixed_fuel_kg):
        order = np.argsort(fuel)
        estimated_range = float(np.interp(fixed_fuel_kg, fuel[order], distance[order]))
        status = "interpolated_between_reoptimized_trials"
    elif not feasible.empty:
        estimated_range = float(feasible["target_distance_m"].max())
        status = "lower_bound_no_infeasible_bracket"
    else:
        estimated_range = float(q3.target_distance_m)
        status = "no_feasible_extension_found"

    summary = pd.DataFrame(
        [
            {
                "artifact_id": "q4-T06",
                "method": "local_reoptimized_range_grid_with_linear_interpolation",
                "claim_level": "local_fixed_fuel_range_estimate",
                "fixed_range_m": q3.target_distance_m,
                "fuel_budget_kg": fixed_fuel_kg,
                "estimated_fixed_fuel_range_m": estimated_range,
                "range_gain_vs_fixed_range_m": estimated_range - q3.target_distance_m,
                "range_gain_vs_fixed_range_pct": 100.0 * (estimated_range - q3.target_distance_m) / q3.target_distance_m,
                "trial_count": int(len(trials)),
                "passed_trial_count": int((trials["validation_status"] == "passed").sum()),
                "range_status": status,
                "evidence_file": "questions/q4/artifacts/tables/fixed_fuel_range_trials.csv",
            }
        ]
    )
    return summary, trials


def _extension_frameworks() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact_id": "q4-T05",
                "framework_id": "temperature_realtime_correction",
                "framework_name": "Real-time temperature and density correction",
                "model_change": "Replace ISA atmosphere calls with a temperature-offset or measured-profile atmosphere T(h,t), p(h,t), rho(h,t), a(h,t); re-integrate pressure hydrostatically before evaluating drag, Mach, and fuel penalty.",
                "required_data": "Along-route temperature deviation profile or onboard/forecast temperature field; pressure reference or hydrostatic boundary; timestamped altitude samples.",
                "validation_plan": "Compare corrected atmosphere against q2 hydrostatic temperature scenarios, verify dp/dh=-rho g residual, and rerun q4-T02/T04 under matched temperature offsets.",
                "implementation_interface": "Extend Q2Parameters with temperature profile provider and pass temperature_offset/profile into q4 _rates.",
                "evidence_boundary": "Framework only; no new numerical fuel-saving claim until temperature scenarios are re-optimized.",
                "status": "framework_only",
            },
            {
                "artifact_id": "q4-T05",
                "framework_id": "engine_installation_loss",
                "framework_name": "Engine installation and altitude-dependent thrust loss",
                "model_change": "Replace ideal commanded thrust T with effective thrust eta_install(h,M,T) T and add installation fuel-flow multiplier phi_install(h,M); keep thrust bounds on commanded thrust.",
                "required_data": "Engine deck or empirical installation efficiency table over altitude, Mach, and thrust setting; uncertainty bounds for efficiency multipliers.",
                "validation_plan": "Run zero-loss recovery test, monotonic loss sanity checks, and sensitivity over eta_install={0.95,0.98,1.00}; compare terminal constraints and fuel impact.",
                "implementation_interface": "Add installation_loss_model callable to q4 _rates before drag balance and fuel-flow evaluation.",
                "evidence_boundary": "Framework only; current q4-T02/T04 use ideal installed thrust and must not claim installed-engine accuracy.",
                "status": "framework_only",
            },
        ]
    )


def run_pipeline(
    *,
    config_path: str,
    nodes: int,
    control_knots: int,
    maxiter: int,
    beta_factors: list[float],
    range_factors: list[float],
    sensitivity_maxiter: int,
    range_maxiter: int,
    skip_beta_sensitivity: bool = False,
    skip_range_extension: bool = False,
    skip_extension_frameworks: bool = False,
) -> dict[str, Path]:
    if nodes < 11:
        raise ValueError("--nodes must be at least 11")
    if control_knots < 3:
        raise ValueError("--control-knots must be at least 3")
    root = project_root()
    qdir = root / "questions" / "q4"
    q3 = load_q3_config(root, config_path)
    params = Q2Parameters(terminal_mass_kg=q3.terminal_mass_min_kg)
    source = _load_no_wind_trajectory(root)
    q2_baseline = _load_q2_standard_baseline(root)
    q1_constant_speed = _load_q1_constant_speed_summary(root)
    q1_profile = _load_q1_constant_speed_profile(root)

    evaluation, optimizer_result, final_vector = _solve_wind_optimal(
        q3=q3,
        params=params,
        source=source,
        nodes=nodes,
        control_knots=control_knots,
        maxiter=maxiter,
    )
    validation_evaluation = _evaluate_controls(
        final_vector,
        q3=q3,
        params=params,
        control_knots=control_knots,
        nodes=max(241, nodes * 3),
    )
    fuel_identity_residual = _fuel_identity_residual(validation_evaluation.trajectory, params)
    wind_results = _wind_result_row(
        evaluation,
        q3=q3,
        params=params,
        optimizer_result=optimizer_result,
        continuation_nodes=str(nodes),
        control_knots=control_knots,
        fuel_identity_residual_kg=fuel_identity_residual,
    )
    comparison = _strategy_comparison(
        q2_baseline=q2_baseline,
        q1_constant_speed=q1_constant_speed,
        wind_results=wind_results,
    )

    outputs: dict[str, Path] = {}
    outputs.update({f"wind_optimal_results_{key}": value for key, value in save_table(wind_results, stem="wind_optimal_results", question_dir=qdir).items()})
    outputs.update({f"wind_optimal_trajectory_{key}": value for key, value in save_table(evaluation.trajectory, stem="wind_optimal_trajectory", question_dir=qdir).items()})
    outputs.update({f"strategy_comparison_{key}": value for key, value in save_table(comparison, stem="strategy_comparison", question_dir=qdir).items()})
    if not skip_beta_sensitivity:
        beta = _beta_sensitivity(
            q3=q3,
            nominal_params=params,
            source=source,
            nominal_evaluation=evaluation,
            nominal_optimizer_result=optimizer_result,
            nominal_vector=final_vector,
            nodes=nodes,
            control_knots=control_knots,
            maxiter=sensitivity_maxiter,
            beta_factors=beta_factors,
        )
        outputs.update({f"beta_sensitivity_{key}": value for key, value in save_table(beta, stem="beta_sensitivity", question_dir=qdir).items()})
    if not skip_range_extension:
        range_summary, range_trials = _range_extension(
            q3=q3,
            params=params,
            source=source,
            q1_profile=q1_profile,
            nominal_evaluation=evaluation,
            nominal_optimizer_result=optimizer_result,
            nominal_vector=final_vector,
            nodes=nodes,
            control_knots=control_knots,
            maxiter=range_maxiter,
            range_factors=range_factors,
        )
        outputs.update({f"fixed_fuel_range_{key}": value for key, value in save_table(range_summary, stem="fixed_fuel_range", question_dir=qdir).items()})
        outputs.update({f"fixed_fuel_range_trials_{key}": value for key, value in save_table(range_trials, stem="fixed_fuel_range_trials", question_dir=qdir).items()})
    if not skip_extension_frameworks:
        extensions = _extension_frameworks()
        outputs.update({f"extension_frameworks_{key}": value for key, value in save_table(extensions, stem="extension_frameworks", question_dir=qdir).items()})
    return outputs


def main() -> int:
    args = parse_args()
    root = project_root()
    question_dir = root / "questions" / "q4"

    steps = [
        "load q1/q2/q3 upstream artifacts",
        "initialize configured-wind reduced-control shooting from q3 no-wind trajectory",
        "solve q4-T02 wind-aware fixed-range fuel objective",
        "save wind_optimal_results and wind_optimal_trajectory",
        "build q4-T03 fixed-range strategy comparison",
        "validate terminal state, constraints, mass floor, and fuel identity",
        "rerun beta sensitivity by scenario and save q4-T04",
        "estimate fixed-fuel local range extension and save q4-T06",
        "save q4-T05 extension frameworks",
    ]
    if args.dry_run:
        print("q4 planned pipeline:")
        for index, step in enumerate(steps, start=1):
            print(f"  {index}. {step}")
        print(f"question_dir={question_dir}")
        print(f"config={root / args.config}")
        print(f"nodes={args.nodes}")
        print(f"control_knots={args.control_knots}")
        return 0

    outputs = run_pipeline(
        config_path=args.config,
        nodes=args.nodes,
        control_knots=args.control_knots,
        maxiter=args.maxiter,
        beta_factors=_parse_float_list(args.beta_factors, option_name="--beta-factors"),
        range_factors=_parse_float_list(args.range_factors, option_name="--range-factors"),
        sensitivity_maxiter=args.sensitivity_maxiter,
        range_maxiter=args.range_maxiter,
        skip_beta_sensitivity=args.skip_beta_sensitivity,
        skip_range_extension=args.skip_range_extension,
        skip_extension_frameworks=args.skip_extension_frameworks,
    )
    for name, path in sorted(outputs.items()):
        print(f"{name}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
