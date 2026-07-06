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
    profiles = [
        pd.read_csv(data_dir / "q2_standard_profile.csv"),
        pd.read_csv(data_dir / "q2_temperature_corrected_profile.csv"),
    ]
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
        data=figure_data[["scenario", "distance_m", "fuel_flow_kgs", "fuel_per_meter_kgpm", "height_m", "temperature_k", "density_kgm3"]],
        stem="fuel_rate_path",
        question_dir=qdir,
        title="q2 fuel-rate distribution along fixed range",
        source_script="questions/q2/scripts/visualize.py",
        notes="standard ISA and +10 K full non-standard atmosphere correction",
    )
    plt.close(fig)


def main() -> int:
    create_figures(ROOT)
    print("q2 figures generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
