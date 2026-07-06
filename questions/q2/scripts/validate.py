#!/usr/bin/env python3
"""Validation and sensitivity analysis for q2."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [SRC, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from modeling_common.artifacts import save_table  # noqa: E402
from fuel_path_model import Q2Parameters  # noqa: E402


def _load_outputs(root: Path) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    data_dir = root / "artifacts" / "q2" / "data"
    summary = pd.read_csv(data_dir / "q2_fuel_summary.csv")
    profiles = {
        "standard_isa": pd.read_csv(data_dir / "q2_standard_profile.csv"),
        "temp_plus_10K": pd.read_csv(data_dir / "q2_temperature_corrected_profile.csv"),
    }
    return summary, profiles


def validation_summary(root: Path | None = None, params: Q2Parameters | None = None) -> pd.DataFrame:
    root = root or ROOT
    params = params or Q2Parameters()
    summary, profiles = _load_outputs(root)
    rows: list[dict[str, object]] = []
    for scenario, frame in profiles.items():
        final_distance = float(frame["distance_m"].iloc[-1])
        rows.extend(
            [
                {
                    "check": "fixed_range_error",
                    "scenario": scenario,
                    "value": abs(final_distance - params.reference_distance_m),
                    "threshold": 1.0,
                    "passed": bool(abs(final_distance - params.reference_distance_m) < 1.0),
                    "notes": "terminal distance matches q1 constant-speed reference range",
                },
                {
                    "check": "positive_fuel_rate",
                    "scenario": scenario,
                    "value": float(frame["fuel_flow_kgs"].min()),
                    "threshold": 0.0,
                    "passed": bool((frame["fuel_flow_kgs"] > 0).all()),
                    "notes": "fuel flow remains positive along path",
                },
                {
                    "check": "positive_atmosphere",
                    "scenario": scenario,
                    "value": float(min(frame["temperature_k"].min(), frame["density_kgm3"].min(), frame["sound_speed_mps"].min())),
                    "threshold": 0.0,
                    "passed": bool(
                        (frame["temperature_k"] > 0).all()
                        and (frame["density_kgm3"] > 0).all()
                        and (frame["sound_speed_mps"] > 0).all()
                    ),
                    "notes": "temperature, density, and sound speed remain physical",
                },
                {
                    "check": "implicit_denominator_positive",
                    "scenario": scenario,
                    "value": float(frame["implicit_denominator"].min()),
                    "threshold": 0.1,
                    "passed": bool((frame["implicit_denominator"] > 0.1).all()),
                    "notes": "implicit mass ODE denominator stays away from zero",
                },
            ]
        )
    standard = float(summary.loc[summary["scenario"] == "standard_isa", "fuel_used_kg"].iloc[0])
    corrected = float(summary.loc[summary["scenario"] == "temp_plus_10K", "fuel_used_kg"].iloc[0])
    delta = corrected - standard
    rows.append(
        {
            "check": "temperature_correction_effect",
            "scenario": "temp_plus_10K",
            "value": delta,
            "threshold": 0.0,
            "passed": bool(abs(delta) > 1e-6),
            "notes": "full non-standard atmosphere correction changes fixed-range fuel",
        }
    )
    return pd.DataFrame(rows)


def run_validation(config_path: str | None = None, root: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    del config_path
    root = root or ROOT
    validation = validation_summary(root)
    qdir = root / "questions" / "q2"
    save_table(validation, stem="validation_summary", question_dir=qdir)
    return validation, pd.DataFrame()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate q2 outputs")
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args()
    validation, _ = run_validation(args.config, ROOT)
    failed = validation[~validation["passed"]]
    if not failed.empty:
        print(failed.to_string(index=False))
        return 1
    print("q2 validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
