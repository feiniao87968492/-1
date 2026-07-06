#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def discover_questions() -> list[Path]:
    return sorted(
        p for p in (ROOT / "questions").glob("q*") if p.is_dir() and p.name[1:].isdigit()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all question pipelines")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print commands without running; default")
    mode.add_argument("--execute", action="store_true", help="Execute implemented pipelines")
    parser.add_argument("--question", action="append", help="Run only selected IDs, e.g. --question q1")
    parser.add_argument("--config", default="configs/default.yaml")
    args = parser.parse_args()

    selected = set(args.question or [])
    questions = [q for q in discover_questions() if not selected or q.name in selected]
    if not questions:
        print("No matching question directories found")
        return 1

    commands = [
        [sys.executable, str(q / "scripts" / "pipeline.py"), "--config", args.config]
        for q in questions
    ]
    if not args.execute:
        for command in commands:
            print(" ".join(command))
        return 0

    for q, command in zip(questions, commands, strict=True):
        print(f"[run] {q.name}")
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode != 0:
            print(f"[error] {q.name} failed with exit code {result.returncode}")
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
