#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
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
from simulate import run_from_config  # noqa: E402
from validate import run_validation  # noqa: E402
from visualize import create_figures  # noqa: E402

IMPLEMENTED = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="q1 modeling pipeline")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _write_profiles(root: Path, outputs: dict[str, object]) -> None:
    root_data_dir = root / "artifacts" / "q1" / "data"
    root_data_dir.mkdir(parents=True, exist_ok=True)
    for strategy, frame in outputs.items():
        frame.to_csv(root_data_dir / f"{strategy}_profile.csv", index=False)


def _mirror_table_to_required_path(root: Path, source: Path, target_name: str) -> None:
    root_data_dir = root / "artifacts" / "q1" / "data"
    root_data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, root_data_dir / target_name)


def main() -> int:
    args = parse_args()
    root = project_root()
    question_dir = root / "questions" / "q1"
    config_path = str(root / args.config)

    steps = [
        "load and validate confirmed q1 parameters",
        "simulate constant-speed and constant-Mach strategies",
        "save full time-series profiles",
        "save strategy comparison tables",
        "run validation and sensitivity analysis",
        "create paired figures, figure data, and metadata",
    ]
    if args.dry_run:
        print("q1 implemented pipeline:")
        for index, step in enumerate(steps, start=1):
            print(f"  {index}. {step}")
        print(f"question_dir={question_dir}")
        print(f"config={root / args.config}")
        return 0

    params, outputs, comparison = run_from_config(config_path)
    _write_profiles(root, outputs)

    table_paths = save_table(comparison, stem="strategy_comparison", question_dir=question_dir)
    _mirror_table_to_required_path(root, table_paths["csv"], "strategy_comparison.csv")

    validation, sensitivity = run_validation(config_path, root)
    create_figures(root)

    print("q1 pipeline completed")
    print(comparison.to_string(index=False))
    if not validation["passed"].all():
        print(validation[~validation["passed"]].to_string(index=False))
        return 1
    if sensitivity.empty:
        return 1
    _ = params
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
