#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ROOT = [
    "README.md",
    "AGENTS.md",
    "agent.md",
    "devlog.md",
    "configs/default.yaml",
    "docs/problem_statement.md",
    "docs/assumptions.md",
    "docs/data_dictionary.md",
    "docs/evidence_chain.csv",
    "docs/figure_table_registry.csv",
    "docs/reproduction.md",
]
REQUIRED_QUESTION = [
    "README.md",
    "manifest.yaml",
    "approach.md",
    "evidence.md",
    "experiments.md",
    "results.md",
    "scripts/pipeline.py",
    "scripts/validate.py",
    "scripts/visualize.py",
]
FIGURE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
DATA_EXTENSIONS = {".csv", ".parquet", ".xlsx", ".json"}
PLACEHOLDER_PATTERN = re.compile(r"\b(TODO|TBD|待填写)\b", re.IGNORECASE)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_ROOT:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")

    question_dirs = sorted(
        p for p in (ROOT / "questions").glob("q*") if p.is_dir() and p.name[1:].isdigit()
    )
    if not question_dirs:
        errors.append("no question directories found under questions/qN")

    for qdir in question_dirs:
        for rel in REQUIRED_QUESTION:
            if not (qdir / rel).exists():
                errors.append(f"{qdir.name}: missing {rel}")

        for doc_name in ["approach.md", "results.md"]:
            path = qdir / doc_name
            if path.exists() and PLACEHOLDER_PATTERN.search(path.read_text(encoding="utf-8")):
                warnings.append(f"{qdir.name}: unresolved placeholders remain in {doc_name}")

        figure_dir = qdir / "artifacts" / "figures"
        data_dir = qdir / "artifacts" / "figure_data"
        if figure_dir.exists():
            for fig in sorted(p for p in figure_dir.iterdir() if p.suffix.lower() in FIGURE_EXTENSIONS):
                matching = [data_dir / f"{fig.stem}{ext}" for ext in DATA_EXTENSIONS]
                if not any(path.exists() for path in matching):
                    errors.append(f"{qdir.name}: figure has no same-stem source data: {fig.name}")
                metadata = data_dir / f"{fig.stem}.meta.json"
                if not metadata.exists():
                    warnings.append(f"{qdir.name}: figure metadata missing: {metadata.name}")

        pipeline = qdir / "scripts" / "pipeline.py"
        if pipeline.exists() and "IMPLEMENTED = False" in pipeline.read_text(encoding="utf-8"):
            warnings.append(f"{qdir.name}: pipeline still marked IMPLEMENTED = False")

    evidence_path = ROOT / "docs" / "evidence_chain.csv"
    if evidence_path.exists():
        required_columns = {
            "claim_id", "question", "claim", "evidence_type", "data_source", "script",
            "config", "artifact", "validation", "status", "notes"
        }
        with evidence_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            if not required_columns.issubset(columns):
                errors.append("docs/evidence_chain.csv has missing required columns")
            else:
                for row_number, row in enumerate(reader, start=2):
                    if row.get("status") == "supported":
                        missing = [field for field in ["data_source", "script", "config", "artifact", "validation"] if not row.get(field)]
                        if missing:
                            errors.append(
                                f"evidence row {row_number} ({row.get('claim_id')}): supported but missing {', '.join(missing)}"
                            )

    if warnings:
        print("Warnings:")
        for item in warnings:
            print(f"  - {item}")
    if errors:
        print("Errors:")
        for item in errors:
            print(f"  - {item}")
        print(f"\nRepository check failed: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1

    print(f"Repository check passed with {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
