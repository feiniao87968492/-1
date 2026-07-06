#!/usr/bin/env python3
"""Paper-level visualization for q2."""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modeling_common.artifacts import save_figure_bundle  # noqa: E402


def create_figures(root: Path | None = None) -> None:
    root = root or ROOT
    qdir = root / "questions" / "q2"
    data_dir = root / "artifacts" / "q2" / "data"
    summary = pd.read_csv(data_dir / "q2_fuel_summary.csv")
    profiles = []
    for scenario in ["standard_isa", "temp_plus_10K"]:
        path = data_dir / "q2_standard_profile.csv" if scenario == "standard_isa" else data_dir / "q2_temperature_corrected_profile.csv"
        profiles.append(pd.read_csv(path))
    figure_data = pd.concat(profiles, ignore_index=True)

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for scenario, frame in figure_data.groupby("scenario"):
        ax.plot(frame["distance_m"] / 1000.0, frame["fuel_flow_kgs"], label=scenario)
    ax.set_xlabel("Ground distance (km)")
    ax.set_ylabel("Fuel flow (kg/s)")
    ax.set_title("q2 fuel-rate distribution along fixed range")
    ax.grid(True, alpha=0.3)
    ax.legend()
    save_figure_bundle(
        fig=fig,
        data=figure_data[
            [
                "scenario",
                "distance_m",
                "fuel_flow_kgs",
                "fuel_per_meter_kgpm",
                "cumulative_fuel_path_kg",
                "height_m",
                "mass_kg",
                "temperature_k",
                "density_kgm3",
            ]
        ],
        stem="fuel_rate_path",
        question_dir=qdir,
        title="q2 fuel-rate distribution along fixed range",
        source_script="questions/q2/scripts/visualize.py",
        notes="standard ISA and +10 K hydrostatic non-standard atmosphere correction",
    )
    plt.close(fig)

    atmosphere_data = figure_data[
        ["scenario", "distance_m", "temperature_k", "density_kgm3", "sound_speed_mps", "pressure_pa"]
    ].copy()
    fig, axes = plt.subplots(3, 1, figsize=(7.0, 7.2), sharex=True)
    for scenario, frame in atmosphere_data.groupby("scenario"):
        distance_km = frame["distance_m"] / 1000.0
        axes[0].plot(distance_km, frame["temperature_k"], label=scenario)
        axes[1].plot(distance_km, frame["density_kgm3"], label=scenario)
        axes[2].plot(distance_km, frame["sound_speed_mps"], label=scenario)
    axes[0].set_ylabel("T (K)")
    axes[1].set_ylabel("rho (kg/m^3)")
    axes[2].set_ylabel("a (m/s)")
    axes[2].set_xlabel("Ground distance (km)")
    for ax in axes:
        ax.grid(True, alpha=0.3)
    axes[0].legend()
    fig.suptitle("q2 atmospheric fields along fixed range")
    save_figure_bundle(
        fig=fig,
        data=atmosphere_data,
        stem="atmosphere_path",
        question_dir=qdir,
        title="q2 atmospheric fields along fixed range",
        source_script="questions/q2/scripts/visualize.py",
        notes="temperature, density, sound speed, and pressure for ISA and +10 K scenarios",
    )
    plt.close(fig)

    sensitivity = pd.read_csv(data_dir / "q2_temperature_sensitivity.csv")
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.plot(
        sensitivity["temperature_offset_k"],
        sensitivity["fuel_delta_vs_standard_pct"],
        marker="o",
        color="#3b6ea8",
    )
    ax.axhline(0.0, color="#555555", linewidth=1.0)
    ax.axhline(1.0, color="#999999", linewidth=0.8, linestyle="--")
    ax.axhline(-1.0, color="#999999", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Temperature offset (K)")
    ax.set_ylabel("Fuel change vs ISA (%)")
    ax.set_title("q2 fixed-range fuel sensitivity to temperature offset")
    ax.grid(True, alpha=0.3)
    save_figure_bundle(
        fig=fig,
        data=sensitivity,
        stem="temperature_sensitivity",
        question_dir=qdir,
        title="q2 fixed-range fuel sensitivity to temperature offset",
        source_script="questions/q2/scripts/visualize.py",
        notes="hydrostatic constant-offset atmosphere; equal true airspeed and fixed CL reference operation",
    )
    plt.close(fig)


def main() -> int:
    create_figures(ROOT)
    print("q2 figures generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
