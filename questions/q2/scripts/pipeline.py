#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCRIPT_DIR = Path(__file__).resolve().parent
for path in [SRC, SCRIPT_DIR]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from modeling_common.artifacts import save_table  # noqa: E402
from modeling_common.paths import project_root  # noqa: E402
from fuel_path_model import Q2Parameters, fuel_summary, simulate_temperature_scenarios  # noqa: E402
from validate import run_validation  # noqa: E402
from visualize import create_figures  # noqa: E402

IMPLEMENTED = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q2 modeling pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = project_root()
    question_dir = root / "questions" / "q2"

    steps = [
        "load and validate inputs",
        "preprocess data",
        "run baseline",
        "fit or solve main model",
        "validate and diagnose",
        "run sensitivity analysis",
        "save tables, figures, figure data, and metadata",
        "update evidence records",
    ]
    if args.dry_run:
        print("q2 planned pipeline:")
        for index, step in enumerate(steps, start=1):
            print(f"  {index}. {step}")
        print(f"question_dir={question_dir}")
        print(f"config={root / args.config}")
        return 0

    params = Q2Parameters()
    data_dir = root / "artifacts" / "q2" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    profiles = simulate_temperature_scenarios(params)
    for scenario, profile in profiles.items():
        profile.to_csv(data_dir / f"q2_{scenario}_profile.csv", index=False)
    profiles["standard_isa"].to_csv(data_dir / "q2_standard_profile.csv", index=False)
    profiles["temp_plus_10K"].to_csv(data_dir / "q2_temperature_corrected_profile.csv", index=False)
    summary = fuel_summary(profiles, params)
    summary.to_csv(data_dir / "q2_fuel_summary.csv", index=False)
    sensitivity = summary[
        [
            "scenario",
            "temperature_offset_k",
            "fuel_used_kg",
            "fuel_delta_vs_standard_kg",
            "fuel_delta_vs_standard_pct",
            "final_time_s",
            "final_mass_kg",
        ]
    ].copy()
    sensitivity.to_csv(data_dir / "q2_temperature_sensitivity.csv", index=False)
    save_table(summary, stem="fuel_summary", question_dir=question_dir)
    save_table(sensitivity, stem="temperature_sensitivity", question_dir=question_dir)
    validation, _ = run_validation(args.config, root)
    create_figures(root)
    print("q2 pipeline completed")
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
