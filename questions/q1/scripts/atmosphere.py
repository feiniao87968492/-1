from __future__ import annotations

import math

RHO0_KGM3 = 1.225
H_RHO_M = 7300.0
T0_K = 288.15
LAPSE_KPM = 0.0065
GAMMA_AIR = 1.4
R_AIR = 287.05
WIND_BASE_MPS = 20.0
WIND_QUAD_COEFF = 3.0e-5
WIND_REF_HEIGHT_M = 10_000.0


def density_kgm3(height_m: float, *, rho0: float = RHO0_KGM3, scale_height_m: float = H_RHO_M) -> float:
    """Return exponential atmosphere density at altitude in meters."""
    if scale_height_m <= 0:
        raise ValueError("Density scale height must be positive")
    density = rho0 * math.exp(-height_m / scale_height_m)
    if density <= 0 or not math.isfinite(density):
        raise ValueError(f"Non-physical density at height={height_m}")
    return density


def temperature_k(height_m: float, *, sea_level_temperature_k: float = T0_K) -> float:
    """Return tropospheric standard-atmosphere temperature."""
    temperature = sea_level_temperature_k - LAPSE_KPM * height_m
    if temperature <= 0 or not math.isfinite(temperature):
        raise ValueError(f"Non-physical temperature at height={height_m}")
    return temperature


def sound_speed_mps(height_m: float) -> float:
    """Return speed of sound from ideal-gas standard atmosphere."""
    speed = math.sqrt(GAMMA_AIR * R_AIR * temperature_k(height_m))
    if speed <= 0 or not math.isfinite(speed):
        raise ValueError(f"Non-physical sound speed at height={height_m}")
    return speed


def dln_density_dh(*, scale_height_m: float = H_RHO_M) -> float:
    """Derivative of log density with respect to height."""
    if scale_height_m <= 0:
        raise ValueError("Density scale height must be positive")
    return -1.0 / scale_height_m


def dln_sound_speed_dh(height_m: float) -> float:
    """Derivative of log sound speed with respect to height."""
    return -LAPSE_KPM / (2.0 * temperature_k(height_m))


def wind_speed_mps(height_m: float) -> float:
    """Return user-confirmed along-track wind speed; positive means tailwind."""
    wind = WIND_BASE_MPS + WIND_QUAD_COEFF * (height_m - WIND_REF_HEIGHT_M) ** 2
    if not math.isfinite(wind):
        raise ValueError(f"Non-finite wind speed at height={height_m}")
    return wind
