from __future__ import annotations

from functools import lru_cache

from scipy.optimize import brentq

from aircraft_model import AircraftParameters
from atmosphere import density_kgm3, dln_density_dh, dln_sound_speed_dh, sound_speed_mps


def initial_mach(params: AircraftParameters) -> float:
    return params.v0_mps / sound_speed_mps(params.h0_m)


def airspeed_from_height(height_m: float, params: AircraftParameters) -> float:
    return initial_mach(params) * sound_speed_mps(height_m)


def _mass_ratio_residual(height_m: float, mass_kg: float, params: AircraftParameters) -> float:
    numerator = density_kgm3(height_m) * sound_speed_mps(height_m) ** 2
    denominator = density_kgm3(params.h0_m) * sound_speed_mps(params.h0_m) ** 2
    return numerator / denominator - mass_kg / params.m0_kg


@lru_cache(maxsize=2048)
def _height_from_mass_cached(mass_kg: float, m0_kg: float, mf_kg: float, h0_m: float, v0_mps: float) -> float:
    params = AircraftParameters(m0_kg=m0_kg, mf_kg=mf_kg, h0_m=h0_m, v0_mps=v0_mps)
    if mass_kg <= 0:
        raise ValueError("Mass must be positive")
    if mass_kg > params.m0_kg:
        raise ValueError("Mass cannot exceed initial mass")
    lower = params.h0_m
    upper = 16_000.0
    while _mass_ratio_residual(upper, mass_kg, params) > 0:
        upper += 2000.0
        if upper >= 40_000:
            raise ValueError("Could not bracket constant-Mach height")
    return float(brentq(_mass_ratio_residual, lower, upper, args=(mass_kg, params), xtol=1e-9))


def height_from_mass(mass_kg: float, params: AircraftParameters) -> float:
    """Constant-Mach cruise-climb height from CL closure."""
    return _height_from_mass_cached(mass_kg, params.m0_kg, params.mf_kg, params.h0_m, params.v0_mps)


def derivatives_wrt_mass(mass_kg: float, params: AircraftParameters) -> tuple[float, float]:
    """Return dh/dm and dV/dm for constant Mach."""
    height_m = height_from_mass(mass_kg, params)
    denom = dln_density_dh() + 2.0 * dln_sound_speed_dh(height_m)
    if denom >= 0:
        raise ValueError("Constant-Mach lift-balance derivative has wrong sign")
    dh_dm = 1.0 / (mass_kg * denom)
    d_v_dh = airspeed_from_height(height_m, params) * dln_sound_speed_dh(height_m)
    return dh_dm, d_v_dh * dh_dm
