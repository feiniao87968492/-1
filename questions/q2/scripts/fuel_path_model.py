from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp


@dataclass(frozen=True)
class Q2Parameters:
    m0_kg: float = 72_450.0
    wing_area_m2: float = 112.3
    cd0: float = 0.022
    induced_k: float = 0.045
    c_t_kg_per_ns: float = 2.8e-4
    beta_s2pm2: float = 0.003
    v_opt_mps: float = 235.0
    h0_m: float = 9500.0
    v0_mps: float = 240.0
    reference_distance_m: float = 200_668.44247343735
    temperature_offset_k: float = 10.0
    temperature_offsets_k: tuple[float, ...] = (-10.0, -5.0, -2.0, 0.0, 2.0, 5.0, 10.0)
    g_mps2: float = 9.80665
    rtol: float = 1.0e-8
    atol: float = 1.0e-9
    max_step_s: float = 2.0


RHO0_KGM3 = 1.225
P0_PA = 101_325.0
T0_K = 288.15
LAPSE_KPM = 0.0065
GAMMA_AIR = 1.4
R_AIR = 287.05
WIND_BASE_MPS = 20.0
WIND_QUAD_COEFF = 3.0e-5
WIND_REF_HEIGHT_M = 10_000.0


def isa_temperature_k(height_m: float) -> float:
    temperature = T0_K - LAPSE_KPM * height_m
    if temperature <= 0:
        raise ValueError(f"Non-physical ISA temperature at height={height_m}")
    return temperature


def isa_pressure_pa(height_m: float) -> float:
    temperature = isa_temperature_k(height_m)
    exponent = 9.80665 / (R_AIR * LAPSE_KPM)
    pressure = P0_PA * (temperature / T0_K) ** exponent
    if pressure <= 0:
        raise ValueError(f"Non-physical ISA pressure at height={height_m}")
    return pressure


def corrected_pressure_pa(height_m: float, *, temperature_offset_k: float = 0.0) -> float:
    """Return hydrostatic pressure for a constant temperature offset in the troposphere."""
    sea_level_temperature = T0_K + temperature_offset_k
    temperature = sea_level_temperature - LAPSE_KPM * height_m
    if sea_level_temperature <= 0 or temperature <= 0:
        raise ValueError(f"Non-physical corrected temperature at height={height_m}")
    exponent = 9.80665 / (R_AIR * LAPSE_KPM)
    pressure = P0_PA * (temperature / sea_level_temperature) ** exponent
    if pressure <= 0:
        raise ValueError(f"Non-physical corrected pressure at height={height_m}")
    return pressure


def atmosphere(height_m: float, *, temperature_offset_k: float = 0.0) -> tuple[float, float, float, float]:
    """Return temperature, density, sound speed, and hydrostatic pressure."""
    temperature = isa_temperature_k(height_m) + temperature_offset_k
    if temperature <= 0:
        raise ValueError(f"Non-physical corrected temperature at height={height_m}")
    pressure = corrected_pressure_pa(height_m, temperature_offset_k=temperature_offset_k)
    density = pressure / (R_AIR * temperature)
    sound_speed = math.sqrt(GAMMA_AIR * R_AIR * temperature)
    return temperature, density, sound_speed, pressure


def wind_speed_mps(height_m: float) -> float:
    return WIND_BASE_MPS + WIND_QUAD_COEFF * (height_m - WIND_REF_HEIGHT_M) ** 2


def constant_cl_height_from_mass(mass_kg: float, params: Q2Parameters, *, temperature_offset_k: float = 0.0) -> float:
    """Solve the constant-speed, constant-CL cruise-climb height under the chosen atmosphere."""
    _, rho_initial, _, _ = atmosphere(params.h0_m, temperature_offset_k=temperature_offset_k)
    target_density = rho_initial * mass_kg / params.m0_kg
    low, high = 0.0, 16_000.0
    for _ in range(80):
        mid = 0.5 * (low + high)
        _, rho_mid, _, _ = atmosphere(mid, temperature_offset_k=temperature_offset_k)
        if rho_mid > target_density:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def _rates(mass_kg: float, params: Q2Parameters, *, temperature_offset_k: float) -> dict[str, float]:
    height_m = constant_cl_height_from_mass(mass_kg, params, temperature_offset_k=temperature_offset_k)
    temperature_k, density_kgm3, sound_speed_mps, pressure_pa = atmosphere(
        height_m, temperature_offset_k=temperature_offset_k
    )
    dh_dm = _dh_dm_numeric(mass_kg, params, temperature_offset_k=temperature_offset_k)
    airspeed_mps = params.v0_mps
    cl = 2.0 * mass_kg * params.g_mps2 / (density_kgm3 * airspeed_mps**2 * params.wing_area_m2)
    cd = params.cd0 + params.induced_k * cl**2
    drag_n = 0.5 * density_kgm3 * airspeed_mps**2 * params.wing_area_m2 * cd
    fuel_penalty = 1.0 + params.beta_s2pm2 * (airspeed_mps - params.v_opt_mps) ** 2
    a_term = (mass_kg * params.g_mps2 / airspeed_mps) * dh_dm
    denominator = 1.0 + params.c_t_kg_per_ns * fuel_penalty * a_term
    if denominator <= 0:
        raise ValueError("Implicit mass ODE denominator is non-positive")
    mass_rate_kgs = -params.c_t_kg_per_ns * fuel_penalty * drag_n / denominator
    climb_rate_mps = dh_dm * mass_rate_kgs
    thrust_n = drag_n + a_term * mass_rate_kgs
    ground_speed_mps = airspeed_mps + wind_speed_mps(height_m)
    fuel_flow_kgs = -mass_rate_kgs
    return {
        "height_m": height_m,
        "temperature_k": temperature_k,
        "density_kgm3": density_kgm3,
        "sound_speed_mps": sound_speed_mps,
        "pressure_pa": pressure_pa,
        "airspeed_mps": airspeed_mps,
        "groundspeed_mps": ground_speed_mps,
        "mach": airspeed_mps / sound_speed_mps,
        "cl": cl,
        "drag_n": drag_n,
        "thrust_n": thrust_n,
        "fuel_flow_kgs": fuel_flow_kgs,
        "climb_rate_mps": climb_rate_mps,
        "mass_rate_kgs": mass_rate_kgs,
        "fuel_per_meter_kgpm": fuel_flow_kgs / ground_speed_mps,
        "implicit_denominator": denominator,
    }


def _dh_dm_numeric(mass_kg: float, params: Q2Parameters, *, temperature_offset_k: float) -> float:
    step = max(1.0, mass_kg * 1e-5)
    m_low = max(mass_kg - step, params.m0_kg * 0.5)
    m_high = min(mass_kg + step, params.m0_kg)
    h_low = constant_cl_height_from_mass(m_low, params, temperature_offset_k=temperature_offset_k)
    h_high = constant_cl_height_from_mass(m_high, params, temperature_offset_k=temperature_offset_k)
    return (h_high - h_low) / (m_high - m_low)


def simulate_fixed_range(
    scenario: str,
    *,
    params: Q2Parameters | None = None,
    temperature_offset_k: float = 0.0,
) -> pd.DataFrame:
    params = params or Q2Parameters()

    def rhs(_time_s: float, state: np.ndarray) -> list[float]:
        mass_kg = float(state[0])
        rates = _rates(mass_kg, params, temperature_offset_k=temperature_offset_k)
        return [rates["mass_rate_kgs"], rates["groundspeed_mps"]]

    def target_distance(_time_s: float, state: np.ndarray) -> float:
        return float(state[1] - params.reference_distance_m)

    target_distance.terminal = True  # type: ignore[attr-defined]
    target_distance.direction = 1  # type: ignore[attr-defined]

    solution = solve_ivp(
        rhs,
        t_span=(0.0, 30_000.0),
        y0=np.array([params.m0_kg, 0.0]),
        events=target_distance,
        rtol=params.rtol,
        atol=params.atol,
        max_step=params.max_step_s,
    )
    if not solution.success or len(solution.t_events[0]) != 1:
        raise RuntimeError(f"{scenario} integration failed: {solution.message}")

    records: list[dict[str, float | str]] = []
    for time_s, mass_kg, distance_m in zip(solution.t, solution.y[0], solution.y[1], strict=True):
        rates = _rates(float(mass_kg), params, temperature_offset_k=temperature_offset_k)
        records.append(
            {
                "scenario": scenario,
                "time_s": float(time_s),
                "distance_m": float(distance_m),
                "mass_kg": float(mass_kg),
                **rates,
            }
        )
    frame = pd.DataFrame.from_records(records)
    frame["cumulative_fuel_time_kg"] = _cumulative_trapezoid(frame["time_s"], frame["fuel_flow_kgs"])
    frame["cumulative_fuel_path_kg"] = _cumulative_trapezoid(frame["distance_m"], frame["fuel_per_meter_kgpm"])
    frame["path_integral_mass_kg"] = params.m0_kg - frame["mass_kg"]
    return frame


def _cumulative_trapezoid(x_values: pd.Series, y_values: pd.Series) -> np.ndarray:
    x = x_values.to_numpy(dtype=float)
    y = y_values.to_numpy(dtype=float)
    cumulative = np.zeros_like(x)
    if len(x) > 1:
        increments = 0.5 * (y[1:] + y[:-1]) * np.diff(x)
        cumulative[1:] = np.cumsum(increments)
    return cumulative


def temperature_scenario_name(offset_k: float) -> str:
    if abs(offset_k) < 1e-12:
        return "standard_isa"
    magnitude = f"{abs(offset_k):g}"
    prefix = "plus" if offset_k > 0 else "minus"
    return f"temp_{prefix}_{magnitude}K"


def simulate_temperature_scenarios(params: Q2Parameters | None = None) -> dict[str, pd.DataFrame]:
    params = params or Q2Parameters()
    return {
        temperature_scenario_name(offset): simulate_fixed_range(
            temperature_scenario_name(offset),
            params=params,
            temperature_offset_k=offset,
        )
        for offset in params.temperature_offsets_k
    }


def fuel_summary(profiles: dict[str, pd.DataFrame], params: Q2Parameters) -> pd.DataFrame:
    rows = []
    for scenario, frame in profiles.items():
        rows.append(
            {
                "scenario": scenario,
                "temperature_offset_k": _scenario_temperature_offset(scenario),
                "final_time_s": frame["time_s"].iloc[-1],
                "final_distance_m": frame["distance_m"].iloc[-1],
                "final_mass_kg": frame["mass_kg"].iloc[-1],
                "fuel_used_kg": params.m0_kg - frame["mass_kg"].iloc[-1],
                "mean_fuel_flow_kgs": (params.m0_kg - frame["mass_kg"].iloc[-1])
                / max(frame["time_s"].iloc[-1], 1e-9),
                "mean_fuel_per_meter_kgpm": (params.m0_kg - frame["mass_kg"].iloc[-1])
                / max(frame["distance_m"].iloc[-1], 1e-9),
                "max_fuel_flow_kgs": frame["fuel_flow_kgs"].max(),
                "min_implicit_denominator": frame["implicit_denominator"].min(),
            }
        )
    summary = pd.DataFrame(rows)
    standard_fuel = float(summary.loc[summary["scenario"] == "standard_isa", "fuel_used_kg"].iloc[0])
    summary["fuel_delta_vs_standard_kg"] = summary["fuel_used_kg"] - standard_fuel
    summary["fuel_delta_vs_standard_pct"] = 100.0 * summary["fuel_delta_vs_standard_kg"] / standard_fuel
    return summary


def _scenario_temperature_offset(scenario: str) -> float:
    if scenario == "standard_isa":
        return 0.0
    parts = scenario.split("_")
    if len(parts) != 3 or parts[0] != "temp":
        raise ValueError(f"Cannot parse temperature offset from scenario={scenario}")
    magnitude = float(parts[2].removesuffix("K"))
    return magnitude if parts[1] == "plus" else -magnitude
