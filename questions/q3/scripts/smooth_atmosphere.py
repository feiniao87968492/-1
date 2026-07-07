from __future__ import annotations

import math

from scipy.integrate import quad

G_MPS2 = 9.80665
R_AIR = 287.05
GAMMA_AIR = 1.4
P0_PA = 101_325.0
T0_K = 288.15
LAPSE_KPM = 0.0065
TROPOPAUSE_M = 11_000.0
DEFAULT_BAND_M = (10_950.0, 11_050.0)


def _isa_temperature_k(height_m: float) -> float:
    return T0_K - LAPSE_KPM * min(height_m, TROPOPAUSE_M)


def _isa_pressure_pa(height_m: float) -> float:
    exponent = G_MPS2 / (R_AIR * LAPSE_KPM)
    if height_m <= TROPOPAUSE_M:
        temperature = _isa_temperature_k(height_m)
        return P0_PA * (temperature / T0_K) ** exponent
    t11 = _isa_temperature_k(TROPOPAUSE_M)
    p11 = _isa_pressure_pa(TROPOPAUSE_M)
    return p11 * math.exp(-G_MPS2 * (height_m - TROPOPAUSE_M) / (R_AIR * t11))


def _smoothstep_temperature_k(height_m: float, band_m: tuple[float, float]) -> float:
    h1, h2 = band_m
    if not h1 < TROPOPAUSE_M < h2:
        raise ValueError("C1 smoothing band must straddle 11000 m")
    if height_m <= h1:
        return _isa_temperature_k(height_m)
    if height_m >= h2:
        return _isa_temperature_k(TROPOPAUSE_M)

    length = h2 - h1
    tau = (height_m - h1) / length
    t_left = _isa_temperature_k(h1)
    t_right = _isa_temperature_k(TROPOPAUSE_M)
    slope_left = -LAPSE_KPM * length
    slope_right = 0.0
    h00 = 2.0 * tau**3 - 3.0 * tau**2 + 1.0
    h10 = tau**3 - 2.0 * tau**2 + tau
    h01 = -2.0 * tau**3 + 3.0 * tau**2
    h11 = tau**3 - tau**2
    return h00 * t_left + h10 * slope_left + h01 * t_right + h11 * slope_right


def _pressure_pa(height_m: float, band_m: tuple[float, float]) -> float:
    h1, h2 = band_m
    if height_m <= h1:
        return _isa_pressure_pa(height_m)

    p1 = _isa_pressure_pa(h1)

    def integrand(height: float) -> float:
        return G_MPS2 / (R_AIR * _smoothstep_temperature_k(height, band_m))

    if height_m <= h2:
        integral, _error = quad(integrand, h1, height_m, epsabs=1.0e-10, epsrel=1.0e-10)
        return p1 * math.exp(-integral)

    integral_band, _error = quad(integrand, h1, h2, epsabs=1.0e-10, epsrel=1.0e-10)
    p2 = p1 * math.exp(-integral_band)
    t2 = _smoothstep_temperature_k(h2, band_m)
    return p2 * math.exp(-G_MPS2 * (height_m - h2) / (R_AIR * t2))


def atmosphere(
    height_m: float,
    *,
    band_m: tuple[float, float] = DEFAULT_BAND_M,
) -> tuple[float, float, float, float]:
    """Return C1 temperature plus hydrostatic pressure, density, and sound speed."""
    temperature_k = _smoothstep_temperature_k(height_m, band_m)
    if temperature_k <= 0.0:
        raise ValueError(f"Non-physical smoothed temperature at height={height_m}")
    pressure_pa = _pressure_pa(height_m, band_m)
    if pressure_pa <= 0.0:
        raise ValueError(f"Non-physical smoothed pressure at height={height_m}")
    density_kgm3 = pressure_pa / (R_AIR * temperature_k)
    sound_speed_mps = math.sqrt(GAMMA_AIR * R_AIR * temperature_k)
    return temperature_k, density_kgm3, sound_speed_mps, pressure_pa


def hydrostatic_residual(
    height_m: float,
    *,
    band_m: tuple[float, float] = DEFAULT_BAND_M,
) -> float:
    """Return the nondimensional hydrostatic residual implied by construction."""
    _temperature_k, density_kgm3, _sound_speed_mps, pressure_pa = atmosphere(height_m, band_m=band_m)
    dp_dh = -G_MPS2 * pressure_pa / (R_AIR * _temperature_k)
    return abs(dp_dh + density_kgm3 * G_MPS2) / max(density_kgm3 * G_MPS2, 1.0e-12)


def temperature_derivative_kpm(
    height_m: float,
    *,
    band_m: tuple[float, float] = DEFAULT_BAND_M,
    step_m: float = 0.01,
) -> float:
    """Return a centered numerical derivative of the smoothed temperature."""
    if step_m <= 0.0:
        raise ValueError("step_m must be positive")
    return (
        _smoothstep_temperature_k(height_m + step_m, band_m)
        - _smoothstep_temperature_k(height_m - step_m, band_m)
    ) / (2.0 * step_m)


def max_deviation_from_layered_isa(
    *,
    height_min_m: float = 10_900.0,
    height_max_m: float = 11_100.0,
    samples: int = 401,
    band_m: tuple[float, float] = DEFAULT_BAND_M,
) -> dict[str, float]:
    max_temperature = 0.0
    max_pressure = 0.0
    max_density = 0.0
    for index in range(samples):
        height = height_min_m + (height_max_m - height_min_m) * index / max(samples - 1, 1)
        t_s, rho_s, _a_s, p_s = atmosphere(height, band_m=band_m)
        t_i = _isa_temperature_k(height)
        p_i = _isa_pressure_pa(height)
        rho_i = p_i / (R_AIR * t_i)
        max_temperature = max(max_temperature, abs(t_s - t_i))
        max_pressure = max(max_pressure, abs(p_s - p_i))
        max_density = max(max_density, abs(rho_s - rho_i))
    return {
        "max_temperature_deviation_k": max_temperature,
        "max_pressure_deviation_pa": max_pressure,
        "max_density_deviation_kgm3": max_density,
    }


def smoothing_diagnostics_table(
    *,
    height_min_m: float = 9_000.0,
    height_max_m: float = 12_500.0,
    samples: int = 701,
    band_m: tuple[float, float] = DEFAULT_BAND_M,
) -> list[dict[str, float | str]]:
    """Return table rows documenting C1 continuity and hydrostatic consistency."""
    if samples < 3:
        raise ValueError("samples must be at least 3")
    heights = [
        height_min_m + (height_max_m - height_min_m) * index / (samples - 1)
        for index in range(samples)
    ]
    temperatures: list[float] = []
    pressures: list[float] = []
    densities: list[float] = []
    hydro_residuals: list[float] = []
    dpdh_values: list[float] = []
    for height in heights:
        temperature_k, density_kgm3, _sound_speed_mps, pressure_pa = atmosphere(height, band_m=band_m)
        temperatures.append(temperature_k)
        pressures.append(pressure_pa)
        densities.append(density_kgm3)
        hydro_residuals.append(hydrostatic_residual(height, band_m=band_m))
        dpdh_values.append(-G_MPS2 * pressure_pa / (R_AIR * temperature_k))

    h1, h2 = band_m
    step_m = 0.01
    t_slope_jump_h1 = abs(
        temperature_derivative_kpm(h1 - step_m, band_m=band_m, step_m=step_m)
        - temperature_derivative_kpm(h1 + step_m, band_m=band_m, step_m=step_m)
    )
    t_slope_jump_11000 = abs(
        temperature_derivative_kpm(TROPOPAUSE_M - step_m, band_m=band_m, step_m=step_m)
        - temperature_derivative_kpm(TROPOPAUSE_M + step_m, band_m=band_m, step_m=step_m)
    )
    t_slope_jump_h2 = abs(
        temperature_derivative_kpm(h2 - step_m, band_m=band_m, step_m=step_m)
        - temperature_derivative_kpm(h2 + step_m, band_m=band_m, step_m=step_m)
    )

    deviations = max_deviation_from_layered_isa(
        height_min_m=h1 - 50.0,
        height_max_m=h2 + 50.0,
        samples=401,
        band_m=band_m,
    )
    rows: list[dict[str, float | str]] = [
        {"metric": "hydrostatic_residual_max", "value": max(hydro_residuals), "unit": "1"},
        {"metric": "temperature_derivative_jump_h1_kpm", "value": t_slope_jump_h1, "unit": "K/m"},
        {"metric": "temperature_derivative_jump_11000_m_kpm", "value": t_slope_jump_11000, "unit": "K/m"},
        {"metric": "temperature_derivative_jump_h2_kpm", "value": t_slope_jump_h2, "unit": "K/m"},
        {"metric": "min_temperature_k", "value": min(temperatures), "unit": "K"},
        {"metric": "min_pressure_pa", "value": min(pressures), "unit": "Pa"},
        {"metric": "min_density_kgm3", "value": min(densities), "unit": "kg/m^3"},
        {"metric": "max_dpdh_pa_per_m", "value": max(dpdh_values), "unit": "Pa/m"},
        {"metric": "min_dpdh_pa_per_m", "value": min(dpdh_values), "unit": "Pa/m"},
    ]
    rows.extend({"metric": key, "value": value, "unit": unit} for key, value, unit in [
        ("max_temperature_deviation_k", deviations["max_temperature_deviation_k"], "K"),
        ("max_pressure_deviation_pa", deviations["max_pressure_deviation_pa"], "Pa"),
        ("max_density_deviation_kgm3", deviations["max_density_deviation_kgm3"], "kg/m^3"),
    ])
    return rows
