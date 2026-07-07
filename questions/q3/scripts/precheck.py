#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
Q2_SCRIPTS = ROOT / "questions" / "q2" / "scripts"
for path in [SRC, Q2_SCRIPTS]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fuel_path_model import Q2Parameters, ReferencePath, atmosphere, load_reference_path  # noqa: E402
from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402


WindModel = Callable[[float], float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q3 pre-solver fixed-path feasibility check")
    parser.add_argument("--config", default="configs/default.yaml")
    return parser.parse_args()


def configured_wind_mps(height_m: float) -> float:
    """User-confirmed wind field W(h)=20+3e-5(h-10000)^2."""
    return 20.0 + 3.0e-5 * (height_m - 10_000.0) ** 2


def no_wind_mps(_height_m: float) -> float:
    return 0.0


def _reference_state(distance_m: float, reference_path: ReferencePath) -> tuple[float, float, float]:
    height_m = float(np.interp(distance_m, reference_path.distance_m, reference_path.height_m))
    airspeed_mps = float(np.interp(distance_m, reference_path.distance_m, reference_path.airspeed_mps))
    dh_dx = float(np.interp(distance_m, reference_path.distance_m, reference_path.dh_dx))
    return height_m, airspeed_mps, dh_dx


def _rates(
    *,
    mass_kg: float,
    distance_m: float,
    params: Q2Parameters,
    reference_path: ReferencePath,
    wind_model: WindModel,
) -> dict[str, float]:
    height_m, airspeed_mps, dh_dx = _reference_state(distance_m, reference_path)
    _temperature_k, density_kgm3, sound_speed_mps, _pressure_pa = atmosphere(height_m)
    cl = 2.0 * mass_kg * params.g_mps2 / (density_kgm3 * airspeed_mps**2 * params.wing_area_m2)
    cd = params.cd0 + params.induced_k * cl**2
    drag_n = 0.5 * density_kgm3 * airspeed_mps**2 * params.wing_area_m2 * cd
    wind_mps = wind_model(height_m)
    ground_speed_mps = airspeed_mps + wind_mps
    if ground_speed_mps <= 0.0:
        raise ValueError(f"Non-positive ground speed at h={height_m:.3f} m")
    climb_rate_mps = dh_dx * ground_speed_mps
    thrust_n = drag_n + mass_kg * params.g_mps2 * climb_rate_mps / airspeed_mps
    fuel_penalty = 1.0 + params.beta_s2pm2 * (airspeed_mps - params.v_opt_mps) ** 2
    fuel_flow_kgs = params.c_t_kg_per_ns * fuel_penalty * thrust_n
    return {
        "height_m": height_m,
        "airspeed_mps": airspeed_mps,
        "dh_dx": dh_dx,
        "wind_mps": wind_mps,
        "groundspeed_mps": ground_speed_mps,
        "mach": airspeed_mps / sound_speed_mps,
        "cl": cl,
        "cd": cd,
        "drag_n": drag_n,
        "thrust_n": thrust_n,
        "fuel_flow_kgs": fuel_flow_kgs,
        "fuel_per_meter_kgpm": fuel_flow_kgs / ground_speed_mps,
        "mass_rate_kgs": -fuel_flow_kgs,
    }


def _cumulative_trapezoid(x_values: pd.Series, y_values: pd.Series) -> np.ndarray:
    x = x_values.to_numpy(dtype=float)
    y = y_values.to_numpy(dtype=float)
    cumulative = np.zeros_like(x)
    if len(x) > 1:
        cumulative[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))
    return cumulative


def simulate_fixed_path(
    *,
    wind_name: str,
    wind_model: WindModel,
    target_distance_m: float,
    params: Q2Parameters,
    reference_path: ReferencePath,
) -> pd.DataFrame:
    if target_distance_m > float(reference_path.distance_m[-1]):
        raise ValueError("q3 target distance exceeds the q1 reference path")

    def rhs(_time_s: float, state: np.ndarray) -> list[float]:
        mass_kg = float(state[0])
        distance_m = float(state[1])
        rates = _rates(
            mass_kg=mass_kg,
            distance_m=distance_m,
            params=params,
            reference_path=reference_path,
            wind_model=wind_model,
        )
        return [rates["mass_rate_kgs"], rates["groundspeed_mps"]]

    def target_event(_time_s: float, state: np.ndarray) -> float:
        return float(state[1] - target_distance_m)

    target_event.terminal = True  # type: ignore[attr-defined]
    target_event.direction = 1  # type: ignore[attr-defined]

    solution = solve_ivp(
        rhs,
        t_span=(0.0, 30_000.0),
        y0=np.array([params.m0_kg, 0.0]),
        events=target_event,
        rtol=params.rtol,
        atol=params.atol,
        max_step=params.max_step_s,
    )
    if not solution.success or len(solution.t_events[0]) != 1:
        raise RuntimeError(f"{wind_name} fixed-path precheck failed: {solution.message}")

    records: list[dict[str, float | str]] = []
    for time_s, mass_kg, distance_m in zip(solution.t, solution.y[0], solution.y[1], strict=True):
        rates = _rates(
            mass_kg=float(mass_kg),
            distance_m=float(distance_m),
            params=params,
            reference_path=reference_path,
            wind_model=wind_model,
        )
        records.append(
            {
                "wind_model": wind_name,
                "time_s": float(time_s),
                "distance_m": float(distance_m),
                "mass_kg": float(mass_kg),
                **rates,
            }
        )
    profile = pd.DataFrame.from_records(records)
    profile["cumulative_fuel_time_kg"] = _cumulative_trapezoid(profile["time_s"], profile["fuel_flow_kgs"])
    profile["cumulative_fuel_path_kg"] = _cumulative_trapezoid(
        profile["distance_m"], profile["fuel_per_meter_kgpm"]
    )
    profile["mass_loss_kg"] = params.m0_kg - profile["mass_kg"]
    return profile


def summarize_profile(
    profile: pd.DataFrame,
    *,
    target_distance_m: float,
    terminal_mass_min_kg: float,
    params: Q2Parameters,
) -> dict[str, float | bool | str]:
    final = profile.iloc[-1]
    fuel_used_kg = params.m0_kg - float(final["mass_kg"])
    final_distance_error_m = float(final["distance_m"]) - target_distance_m
    fuel_integral_error_kg = float(final["cumulative_fuel_time_kg"]) - fuel_used_kg
    terminal_mass_feasible = bool(float(final["mass_kg"]) >= terminal_mass_min_kg)
    distance_feasible = bool(abs(final_distance_error_m) < 1.0)
    integral_feasible = bool(abs(fuel_integral_error_kg) < 0.05)
    return {
        "wind_model": str(final["wind_model"]),
        "target_distance_m": target_distance_m,
        "final_distance_m": float(final["distance_m"]),
        "final_distance_error_m": final_distance_error_m,
        "final_time_s": float(final["time_s"]),
        "final_height_m": float(final["height_m"]),
        "final_airspeed_mps": float(final["airspeed_mps"]),
        "final_mass_kg": float(final["mass_kg"]),
        "fuel_used_kg": fuel_used_kg,
        "fuel_integral_time_kg": float(final["cumulative_fuel_time_kg"]),
        "fuel_integral_path_kg": float(final["cumulative_fuel_path_kg"]),
        "fuel_integral_error_kg": fuel_integral_error_kg,
        "max_thrust_n": float(profile["thrust_n"].max()),
        "min_thrust_n": float(profile["thrust_n"].min()),
        "mean_groundspeed_mps": target_distance_m / float(final["time_s"]),
        "terminal_mass_min_kg": terminal_mass_min_kg,
        "terminal_mass_feasible": terminal_mass_feasible,
        "baseline_feasible": bool(terminal_mass_feasible and distance_feasible and integral_feasible),
    }


def load_q3_config(root: Path, config_path: str) -> dict:
    with (root / config_path).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    q3 = config.get("q3_optimal_control")
    if not isinstance(q3, dict):
        raise ValueError("configs/default.yaml missing q3_optimal_control section")
    return q3


def main() -> int:
    args = parse_args()
    root = project_root()
    q3 = load_q3_config(root, args.config)
    bounds = q3.get("bounds", {})
    target_distance_m = float(q3["fixed_range_m"])
    terminal_mass_min_kg = float(bounds["mass_min_kg"])
    params = Q2Parameters(terminal_mass_kg=terminal_mass_min_kg)
    reference_path = load_reference_path(str(root))

    scenarios: list[tuple[str, WindModel]] = [
        ("configured_wind", configured_wind_mps),
        ("no_wind", no_wind_mps),
    ]
    summaries = []
    for wind_name, wind_model in scenarios:
        profile = simulate_fixed_path(
            wind_name=wind_name,
            wind_model=wind_model,
            target_distance_m=target_distance_m,
            params=params,
            reference_path=reference_path,
        )
        summaries.append(
            summarize_profile(
                profile,
                target_distance_m=target_distance_m,
                terminal_mass_min_kg=terminal_mass_min_kg,
                params=params,
            )
        )

    table = pd.DataFrame(summaries)
    outputs = save_table(table, stem="baseline_feasibility", question_dir=root / "questions" / "q3")
    print(f"saved {outputs['csv']}")
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
