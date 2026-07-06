from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from aircraft_model import (  # noqa: E402
    AircraftParameters,
    drag_n,
    fuel_penalty,
    lift_coefficient,
    load_parameters,
    validate_parameters,
)
from atmosphere import density_kgm3, sound_speed_mps, wind_speed_mps  # noqa: E402
import strategy_constant_mach as mach_strategy  # noqa: E402
import strategy_constant_speed as speed_strategy  # noqa: E402

StrategyFn = Callable[[float, AircraftParameters], float]
DerivativeFn = Callable[[float, AircraftParameters], tuple[float, float]]

REQUIRED_COLUMNS = [
    "time_s",
    "distance_m",
    "mass_kg",
    "height_m",
    "airspeed_mps",
    "groundspeed_mps",
    "mach",
    "density_kgm3",
    "lift_N",
    "drag_N",
    "thrust_N",
    "fuel_flow_kgs",
    "climb_rate_mps",
    "energy_residual",
    "lift_balance_residual",
]


def _rates(
    mass_kg: float,
    height_from_mass: StrategyFn,
    airspeed_from_height: StrategyFn,
    derivatives: DerivativeFn,
    params: AircraftParameters,
) -> dict[str, float]:
    height_m = height_from_mass(mass_kg, params)
    airspeed_mps = airspeed_from_height(height_m, params)
    dh_dm, d_v_dm = derivatives(mass_kg, params)
    drag = drag_n(height_m, airspeed_mps, mass_kg, params)
    penalty = fuel_penalty(airspeed_mps, params)
    a_term = mass_kg * d_v_dm + (mass_kg * params.g_mps2 / airspeed_mps) * dh_dm
    denom = 1.0 + params.c_t_kg_per_ns * penalty * a_term
    if denom <= 0:
        raise ValueError(f"Implicit fuel-flow denominator is non-positive: {denom}")
    mass_rate = -params.c_t_kg_per_ns * penalty * drag / denom
    climb_rate = dh_dm * mass_rate
    acceleration = d_v_dm * mass_rate
    thrust = drag + a_term * mass_rate
    if thrust <= 0:
        raise ValueError("Thrust must remain positive")
    fuel_flow = -mass_rate
    lift = 0.5 * density_kgm3(height_m) * airspeed_mps**2 * params.wing_area_m2 * lift_coefficient(
        height_m, airspeed_mps, mass_kg, params
    )
    groundspeed = airspeed_mps + wind_speed_mps(height_m)
    energy_residual = (thrust - drag - mass_kg * acceleration - mass_kg * params.g_mps2 * climb_rate / airspeed_mps) / max(
        thrust, drag, 1.0
    )
    lift_balance_residual = (lift - mass_kg * params.g_mps2) / (mass_kg * params.g_mps2)
    return {
        "height_m": height_m,
        "airspeed_mps": airspeed_mps,
        "groundspeed_mps": groundspeed,
        "mach": airspeed_mps / sound_speed_mps(height_m),
        "density_kgm3": density_kgm3(height_m),
        "lift_N": lift,
        "drag_N": drag,
        "thrust_N": thrust,
        "fuel_flow_kgs": fuel_flow,
        "climb_rate_mps": climb_rate,
        "mass_rate_kgs": mass_rate,
        "energy_residual": energy_residual,
        "lift_balance_residual": lift_balance_residual,
    }


def simulate_strategy(
    *,
    strategy_name: str,
    height_from_mass: StrategyFn,
    airspeed_from_height: StrategyFn,
    derivatives: DerivativeFn,
    params: AircraftParameters,
) -> pd.DataFrame:
    """Integrate mass and ground distance until the confirmed terminal mass."""
    validate_parameters(params)

    def rhs(_time_s: float, state: np.ndarray) -> list[float]:
        mass_kg = float(state[0])
        rates = _rates(mass_kg, height_from_mass, airspeed_from_height, derivatives, params)
        return [rates["mass_rate_kgs"], rates["groundspeed_mps"]]

    def terminal_mass(_time_s: float, state: np.ndarray) -> float:
        return float(state[0] - params.mf_kg)

    terminal_mass.terminal = True  # type: ignore[attr-defined]
    terminal_mass.direction = -1  # type: ignore[attr-defined]

    solution = solve_ivp(
        rhs,
        t_span=(0.0, 20_000.0),
        y0=np.array([params.m0_kg, 0.0]),
        events=terminal_mass,
        rtol=params.rtol,
        atol=params.atol,
        max_step=params.max_step_s,
        dense_output=False,
    )
    if not solution.success or len(solution.t_events[0]) != 1:
        raise RuntimeError(f"{strategy_name} integration failed: {solution.message}")

    records: list[dict[str, float | str]] = []
    for time_s, mass_kg, distance_m in zip(solution.t, solution.y[0], solution.y[1], strict=True):
        rates = _rates(float(mass_kg), height_from_mass, airspeed_from_height, derivatives, params)
        record: dict[str, float | str] = {
            "strategy": strategy_name,
            "time_s": float(time_s),
            "distance_m": float(distance_m),
            "mass_kg": float(mass_kg),
        }
        record.update({key: rates[key] for key in REQUIRED_COLUMNS if key in rates})
        records.append(record)
    frame = pd.DataFrame.from_records(records)
    frame = frame[["strategy", *REQUIRED_COLUMNS]]
    if not frame["mass_kg"].is_monotonic_decreasing:
        raise RuntimeError(f"{strategy_name} mass is not monotone decreasing")
    return frame


def run_strategies(params: AircraftParameters | None = None) -> dict[str, pd.DataFrame]:
    """Run both confirmed q1 cruise-climb strategies."""
    params = params or AircraftParameters()
    return {
        "constant_speed": simulate_strategy(
            strategy_name="constant_speed",
            height_from_mass=speed_strategy.height_from_mass,
            airspeed_from_height=speed_strategy.airspeed_from_height,
            derivatives=speed_strategy.derivatives_wrt_mass,
            params=params,
        ),
        "constant_mach": simulate_strategy(
            strategy_name="constant_mach",
            height_from_mass=mach_strategy.height_from_mass,
            airspeed_from_height=mach_strategy.airspeed_from_height,
            derivatives=mach_strategy.derivatives_wrt_mass,
            params=params,
        ),
    }


def comparison_table(outputs: dict[str, pd.DataFrame], params: AircraftParameters) -> pd.DataFrame:
    rows = []
    for strategy, frame in outputs.items():
        elapsed_s = frame["time_s"].iloc[-1] - frame["time_s"].iloc[0]
        if elapsed_s <= 0:
            raise ValueError(f"{strategy} elapsed time must be positive")
        mean_climb_rate = (frame["height_m"].iloc[-1] - frame["height_m"].iloc[0]) / elapsed_s
        mean_groundspeed = (frame["distance_m"].iloc[-1] - frame["distance_m"].iloc[0]) / elapsed_s
        if "airspeed_mps" in frame:
            air_distance = float(np.trapezoid(frame["airspeed_mps"], frame["time_s"]))
            wind_distance = float(frame["distance_m"].iloc[-1] - frame["distance_m"].iloc[0] - air_distance)
        else:
            air_distance = float("nan")
            wind_distance = float("nan")
        rows.append(
            {
                "strategy": strategy,
                "final_time_s": frame["time_s"].iloc[-1],
                "final_distance_m": frame["distance_m"].iloc[-1],
                "air_distance_m": air_distance,
                "wind_distance_contribution_m": wind_distance,
                "final_height_m": frame["height_m"].iloc[-1],
                "fuel_used_kg": params.m0_kg - params.mf_kg,
                "mean_climb_rate_mps": mean_climb_rate,
                "max_climb_rate_mps": frame["climb_rate_mps"].max(),
                "mean_groundspeed_mps": mean_groundspeed,
                "max_abs_energy_residual": frame["energy_residual"].abs().max(),
                "max_abs_lift_balance_residual": frame["lift_balance_residual"].abs().max(),
            }
        )
    return pd.DataFrame(rows)


def run_from_config(config_path: str | None = None) -> tuple[AircraftParameters, dict[str, pd.DataFrame], pd.DataFrame]:
    params = load_parameters(config_path)
    outputs = run_strategies(params)
    return params, outputs, comparison_table(outputs, params)
