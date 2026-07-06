from __future__ import annotations

from aircraft_model import AircraftParameters
from atmosphere import H_RHO_M, density_kgm3


def height_from_mass(mass_kg: float, params: AircraftParameters) -> float:
    """Constant-true-airspeed cruise-climb height from CL closure."""
    return params.h0_m - H_RHO_M * __import__("math").log(mass_kg / params.m0_kg)


def airspeed_from_height(height_m: float, params: AircraftParameters) -> float:
    """Constant-speed strategy keeps true airspeed fixed."""
    _ = height_m
    return params.v0_mps


def derivatives_wrt_mass(mass_kg: float, params: AircraftParameters) -> tuple[float, float]:
    """Return dh/dm and dV/dm for constant true airspeed."""
    if mass_kg <= 0:
        raise ValueError("Mass must be positive")
    return -H_RHO_M / mass_kg, 0.0


def density_ratio_residual(mass_kg: float, params: AircraftParameters) -> float:
    """Residual for m/m0 = rho/rho0_at_initial under constant CL and V."""
    height_m = height_from_mass(mass_kg, params)
    return mass_kg / params.m0_kg - density_kgm3(height_m) / density_kgm3(params.h0_m)
