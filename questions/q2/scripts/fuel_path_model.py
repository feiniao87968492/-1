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
    terminal_mass_kg: float = 62_000.0
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
TROPOPAUSE_M = 11_000.0


def isa_temperature_k(height_m: float) -> float:
    temperature = T0_K - LAPSE_KPM * min(height_m, TROPOPAUSE_M)
    if temperature <= 0:
        raise ValueError(f"Non-physical ISA temperature at height={height_m}")
    return temperature


def isa_pressure_pa(height_m: float) -> float:
    exponent = 9.80665 / (R_AIR * LAPSE_KPM)
    if height_m <= TROPOPAUSE_M:
        temperature = isa_temperature_k(height_m)
        pressure = P0_PA * (temperature / T0_K) ** exponent
    else:
        t11 = isa_temperature_k(TROPOPAUSE_M)
        p11 = P0_PA * (t11 / T0_K) ** exponent
        pressure = p11 * math.exp(-9.80665 * (height_m - TROPOPAUSE_M) / (R_AIR * t11))
    if pressure <= 0:
        raise ValueError(f"Non-physical ISA pressure at height={height_m}")
    return pressure


def corrected_pressure_pa(height_m: float, *, temperature_offset_k: float = 0.0) -> float:
    """Return hydrostatic pressure for a constant temperature offset in layered ISA."""
    sea_level_temperature = T0_K + temperature_offset_k
    exponent = 9.80665 / (R_AIR * LAPSE_KPM)
    if height_m <= TROPOPAUSE_M:
        temperature = sea_level_temperature - LAPSE_KPM * height_m
        pressure = P0_PA * (temperature / sea_level_temperature) ** exponent
    else:
        t11 = sea_level_temperature - LAPSE_KPM * TROPOPAUSE_M
        p11 = P0_PA * (t11 / sea_level_temperature) ** exponent
        temperature = t11
        pressure = p11 * math.exp(-9.80665 * (height_m - TROPOPAUSE_M) / (R_AIR * temperature))
    if sea_level_temperature <= 0 or temperature <= 0:
        raise ValueError(f"Non-physical corrected temperature at height={height_m}")
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


def atmosphere_layer(height_m: float) -> str:
    return "troposphere" if height_m <= TROPOPAUSE_M else "lower_stratosphere"


def wind_speed_mps(height_m: float) -> float:
    return WIND_BASE_MPS + WIND_QUAD_COEFF * (height_m - WIND_REF_HEIGHT_M) ** 2


@dataclass(frozen=True)
class ReferencePath:
    distance_m: np.ndarray
    height_m: np.ndarray
    airspeed_mps: np.ndarray
    dh_dx: np.ndarray


def load_reference_path(root: str | None = None) -> ReferencePath:
    from pathlib import Path

    base = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    frame = pd.read_csv(base / "artifacts" / "q1" / "data" / "constant_speed_profile.csv")
    required = {"distance_m", "height_m", "airspeed_mps"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"q1 reference path missing columns: {sorted(missing)}")
    path = frame.sort_values("distance_m").drop_duplicates("distance_m")
    return ReferencePath(
        distance_m=path["distance_m"].to_numpy(dtype=float),
        height_m=path["height_m"].to_numpy(dtype=float),
        airspeed_mps=path["airspeed_mps"].to_numpy(dtype=float),
        dh_dx=np.gradient(
            path["height_m"].to_numpy(dtype=float),
            path["distance_m"].to_numpy(dtype=float),
        ),
    )


def _reference_state(distance_m: float, reference_path: ReferencePath) -> tuple[float, float, float]:
    x = reference_path.distance_m
    h = reference_path.height_m
    v = reference_path.airspeed_mps
    gradient = reference_path.dh_dx
    height_m = float(np.interp(distance_m, x, h))
    airspeed_mps = float(np.interp(distance_m, x, v))
    dh_dx = float(np.interp(distance_m, x, gradient))
    return height_m, airspeed_mps, dh_dx


def _rates(
    mass_kg: float,
    distance_m: float,
    params: Q2Parameters,
    *,
    temperature_offset_k: float,
    reference_path: ReferencePath,
) -> dict[str, float | str]:
    height_m, airspeed_mps, dh_dx = _reference_state(distance_m, reference_path)
    temperature_k, density_kgm3, sound_speed_mps, pressure_pa = atmosphere(
        height_m, temperature_offset_k=temperature_offset_k
    )
    cl = 2.0 * mass_kg * params.g_mps2 / (density_kgm3 * airspeed_mps**2 * params.wing_area_m2)
    cd = params.cd0 + params.induced_k * cl**2
    drag_n = 0.5 * density_kgm3 * airspeed_mps**2 * params.wing_area_m2 * cd
    fuel_penalty = 1.0 + params.beta_s2pm2 * (airspeed_mps - params.v_opt_mps) ** 2
    ground_speed_mps = airspeed_mps + wind_speed_mps(height_m)
    climb_rate_mps = dh_dx * ground_speed_mps
    thrust_n = drag_n + mass_kg * params.g_mps2 * climb_rate_mps / airspeed_mps
    denominator = 1.0
    if denominator <= 0:
        raise ValueError("Implicit mass ODE denominator is non-positive")
    fuel_flow_kgs = params.c_t_kg_per_ns * fuel_penalty * thrust_n
    mass_rate_kgs = -fuel_flow_kgs
    fuel_flow_kgs = -mass_rate_kgs
    return {
        "reference_height_m": height_m,
        "height_m": height_m,
        "temperature_k": temperature_k,
        "density_kgm3": density_kgm3,
        "sound_speed_mps": sound_speed_mps,
        "pressure_pa": pressure_pa,
        "atmosphere_layer": atmosphere_layer(height_m),
        "airspeed_mps": airspeed_mps,
        "groundspeed_mps": ground_speed_mps,
        "mach": airspeed_mps / sound_speed_mps,
        "cl": cl,
        "cd": cd,
        "drag_n": drag_n,
        "thrust_n": thrust_n,
        "fuel_flow_kgs": fuel_flow_kgs,
        "climb_rate_mps": climb_rate_mps,
        "dh_dx": dh_dx,
        "mass_rate_kgs": mass_rate_kgs,
        "fuel_per_meter_kgpm": fuel_flow_kgs / ground_speed_mps,
        "implicit_denominator": denominator,
    }


def simulate_fixed_range(
    scenario: str,
    *,
    params: Q2Parameters | None = None,
    temperature_offset_k: float = 0.0,
    reference_path: ReferencePath | None = None,
    target_distance_m: float | None = None,
    stop_at_terminal_mass: bool = False,
) -> pd.DataFrame:
    params = params or Q2Parameters()
    reference_path = reference_path or load_reference_path()
    target_distance = params.reference_distance_m if target_distance_m is None else target_distance_m

    def rhs(_time_s: float, state: np.ndarray) -> list[float]:
        mass_kg = float(state[0])
        distance_m = float(state[1])
        rates = _rates(
            mass_kg,
            distance_m,
            params,
            temperature_offset_k=temperature_offset_k,
            reference_path=reference_path,
        )
        return [rates["mass_rate_kgs"], rates["groundspeed_mps"]]

    def target_distance_event(_time_s: float, state: np.ndarray) -> float:
        return float(state[1] - target_distance)

    target_distance_event.terminal = True  # type: ignore[attr-defined]
    target_distance_event.direction = 1  # type: ignore[attr-defined]

    def terminal_mass_event(_time_s: float, state: np.ndarray) -> float:
        return float(state[0] - params.terminal_mass_kg)

    terminal_mass_event.terminal = True  # type: ignore[attr-defined]
    terminal_mass_event.direction = -1  # type: ignore[attr-defined]
    events = terminal_mass_event if stop_at_terminal_mass else target_distance_event

    solution = solve_ivp(
        rhs,
        t_span=(0.0, 30_000.0),
        y0=np.array([params.m0_kg, 0.0]),
        events=events,
        rtol=params.rtol,
        atol=params.atol,
        max_step=params.max_step_s,
    )
    if not solution.success or len(solution.t_events[0]) != 1:
        raise RuntimeError(f"{scenario} integration failed: {solution.message}")

    records: list[dict[str, float | str]] = []
    for time_s, mass_kg, distance_m in zip(solution.t, solution.y[0], solution.y[1], strict=True):
        rates = _rates(
            float(mass_kg),
            float(distance_m),
            params,
            temperature_offset_k=temperature_offset_k,
            reference_path=reference_path,
        )
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
    reference_path = load_reference_path()
    terminal_profiles = [
        simulate_fixed_range(
            f"{temperature_scenario_name(offset)}_terminal_mass",
            params=params,
            temperature_offset_k=offset,
            reference_path=reference_path,
            stop_at_terminal_mass=True,
        )
        for offset in params.temperature_offsets_k
    ]
    target_distance_m = min(float(profile["distance_m"].iloc[-1]) for profile in terminal_profiles)
    return {
        temperature_scenario_name(offset): simulate_fixed_range(
            temperature_scenario_name(offset),
            params=params,
            temperature_offset_k=offset,
            reference_path=reference_path,
            target_distance_m=target_distance_m,
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
