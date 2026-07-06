from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

import yaml

from atmosphere import density_kgm3


@dataclass(frozen=True)
class AircraftParameters:
    m0_kg: float = 72_450.0
    mf_kg: float = 62_000.0
    wing_area_m2: float = 112.3
    cd0: float = 0.022
    induced_k: float = 0.045
    c_t_kg_per_ns: float = 2.8e-4
    beta_s2pm2: float = 0.003
    v_opt_mps: float = 235.0
    h0_m: float = 9500.0
    v0_mps: float = 240.0
    g_mps2: float = 9.80665
    rtol: float = 1.0e-8
    atol: float = 1.0e-9
    max_step_s: float = 5.0


def load_parameters(config_path: str | None = None) -> AircraftParameters:
    """Load q1 parameters from a YAML config, falling back to confirmed defaults."""
    params = AircraftParameters()
    if not config_path:
        return params
    with open(config_path, encoding="utf-8") as handle:
        config: dict[str, Any] = yaml.safe_load(handle) or {}
    q1_config = config.get("q1", {})
    mapping = {
        "m0_kg": "m0_kg",
        "mf_kg": "mf_kg",
        "wing_area_m2": "wing_area_m2",
        "cd0": "cd0",
        "induced_k": "induced_k",
        "c_t_kg_per_ns": "c_t_kg_per_ns",
        "beta_s2pm2": "beta_s2pm2",
        "v_opt_mps": "v_opt_mps",
        "h0_m": "h0_m",
        "v0_mps": "v0_mps",
        "g_mps2": "g_mps2",
        "rtol": "rtol",
        "atol": "atol",
        "max_step_s": "max_step_s",
    }
    updates = {field: float(q1_config[key]) for key, field in mapping.items() if key in q1_config}
    return replace(params, **updates)


def validate_parameters(params: AircraftParameters) -> None:
    """Validate ranges and units used by the q1 point-mass model."""
    checks = {
        "m0_kg": params.m0_kg > 0,
        "mf_kg": 0 < params.mf_kg < params.m0_kg,
        "wing_area_m2": params.wing_area_m2 > 0,
        "cd0": params.cd0 > 0,
        "induced_k": params.induced_k > 0,
        "c_t_kg_per_ns": params.c_t_kg_per_ns > 0,
        "beta_s2pm2": params.beta_s2pm2 >= 0,
        "v_opt_mps": params.v_opt_mps > 0,
        "h0_m": params.h0_m >= 0,
        "v0_mps": params.v0_mps > 0,
        "g_mps2": params.g_mps2 > 0,
        "rtol": params.rtol > 0,
        "atol": params.atol > 0,
        "max_step_s": params.max_step_s > 0,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"Invalid q1 parameter(s): {', '.join(failed)}")


def lift_coefficient(height_m: float, airspeed_mps: float, mass_kg: float, params: AircraftParameters) -> float:
    """Compute CL needed to satisfy small-angle lift balance."""
    rho = density_kgm3(height_m)
    return 2.0 * mass_kg * params.g_mps2 / (rho * airspeed_mps**2 * params.wing_area_m2)


def initial_lift_coefficient(params: AircraftParameters) -> float:
    return lift_coefficient(params.h0_m, params.v0_mps, params.m0_kg, params)


def drag_n(height_m: float, airspeed_mps: float, mass_kg: float, params: AircraftParameters) -> float:
    """Return drag using the parabolic polar with lift balance."""
    rho = density_kgm3(height_m)
    cl = lift_coefficient(height_m, airspeed_mps, mass_kg, params)
    cd = params.cd0 + params.induced_k * cl**2
    drag = 0.5 * rho * airspeed_mps**2 * params.wing_area_m2 * cd
    if drag <= 0:
        raise ValueError("Drag must be positive")
    return drag


def fuel_penalty(airspeed_mps: float, params: AircraftParameters) -> float:
    """Dimensionless speed-deviation fuel penalty."""
    penalty = 1.0 + params.beta_s2pm2 * (airspeed_mps - params.v_opt_mps) ** 2
    if penalty < 1.0:
        raise ValueError("Fuel penalty must be at least one")
    return penalty
