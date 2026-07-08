#!/usr/bin/env python3
"""Paper-level visualization for q4."""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modeling_common.artifacts import save_figure_bundle  # noqa: E402


def _read_required_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required q4 figure input is missing: {path}")
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError(f"Required q4 figure input is empty: {path}")
    return frame


def create_figures(root: Path | None = None) -> dict[str, Path]:
    root = root or ROOT
    qdir = root / "questions" / "q4"
    q4_tables = qdir / "artifacts" / "tables"
    q1_data = root / "artifacts" / "q1" / "data"

    trajectory = _read_required_csv(q4_tables / "wind_optimal_trajectory.csv")
    beta = _read_required_csv(q4_tables / "beta_sensitivity.csv")
    q1_profile = _read_required_csv(q1_data / "constant_speed_profile.csv")

    outputs: dict[str, Path] = {}

    q4_height = trajectory[["distance_m", "height_m"]].copy()
    q4_height["strategy"] = "q4_configured_wind_local"
    q1_height = q1_profile.loc[q1_profile["distance_m"] <= trajectory["distance_m"].max(), ["distance_m", "height_m"]].copy()
    q1_height["strategy"] = "q1_constant_speed"
    height_data = pd.concat([q1_height, q4_height], ignore_index=True)

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for strategy, frame in height_data.groupby("strategy"):
        ax.plot(frame["distance_m"] / 1000.0, frame["height_m"], label=strategy)
    ax.set_xlabel("Ground distance (km)")
    ax.set_ylabel("Altitude (m)")
    ax.set_title("q4 altitude profile over fixed range")
    ax.grid(True, alpha=0.3)
    ax.legend()
    outputs.update(
        {
            f"height_range_comparison_{key}": value
            for key, value in save_figure_bundle(
                fig=fig,
                data=height_data,
                stem="height_range_comparison",
                question_dir=qdir,
                title="q4 altitude profile over fixed range",
                source_script="questions/q4/scripts/visualize.py",
                notes="q1 constant-speed baseline truncated to q4 fixed range; q4 configured-wind local shooting trajectory",
            ).items()
        }
    )
    plt.close(fig)

    profile_data = trajectory[
        [
            "distance_m",
            "height_m",
            "airspeed_mps",
            "mass_kg",
            "time_s",
            "thrust_n",
            "gamma_rad",
            "groundspeed_mps",
            "fuel_per_meter_kgpm",
        ]
    ].copy()
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 8.0), sharex=True)
    distance_km = profile_data["distance_m"] / 1000.0
    axes[0].plot(distance_km, profile_data["airspeed_mps"], color="#2f5f8f")
    axes[0].set_ylabel("TAS (m/s)")
    axes[1].plot(distance_km, profile_data["mass_kg"], color="#437f5b")
    axes[1].set_ylabel("Mass (kg)")
    axes[2].plot(distance_km, profile_data["thrust_n"] / 1000.0, color="#9a5a2f")
    axes[2].set_ylabel("Thrust (kN)")
    axes[2].set_xlabel("Ground distance (km)")
    for axis in axes:
        axis.grid(True, alpha=0.3)
    fig.suptitle("q4 configured-wind local trajectory profiles")
    outputs.update(
        {
            f"profile_comparison_{key}": value
            for key, value in save_figure_bundle(
                fig=fig,
                data=profile_data,
                stem="profile_comparison",
                question_dir=qdir,
                title="q4 configured-wind local trajectory profiles",
                source_script="questions/q4/scripts/visualize.py",
                notes="Airspeed, mass, and thrust over fixed common range for q4-T02 local shooting result",
            ).items()
        }
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.plot(beta["beta_factor"], beta["fuel_delta_vs_nominal_kg"], marker="o", color="#3f6f7f")
    ax.axhline(0.0, color="#555555", linewidth=1.0)
    ax.set_xlabel("Beta factor")
    ax.set_ylabel("Fuel change vs nominal (kg)")
    ax.set_title("q4 beta re-optimization sensitivity")
    ax.grid(True, alpha=0.3)
    outputs.update(
        {
            f"beta_sensitivity_{key}": value
            for key, value in save_figure_bundle(
                fig=fig,
                data=beta,
                stem="beta_sensitivity",
                question_dir=qdir,
                title="q4 beta re-optimization sensitivity",
                source_script="questions/q4/scripts/visualize.py",
                notes="Each beta scenario is re-optimized with reduced-control shooting; not a post-solution metric-only recalculation",
            ).items()
        }
    )
    plt.close(fig)

    return outputs


def main() -> int:
    outputs = create_figures(ROOT)
    for name, path in sorted(outputs.items()):
        print(f"{name}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
