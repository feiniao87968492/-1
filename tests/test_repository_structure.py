from pathlib import Path

import pandas as pd

from modeling_common.artifacts import save_table


def test_core_repository_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    required = [
        root / "AGENTS.md",
        root / "docs" / "problem_statement.md",
        root / "docs" / "evidence_chain.csv",
        root / "scripts" / "check_repo.py",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    assert not missing, f"Missing core repository files: {missing}"


def test_save_table_uses_lf_line_endings(tmp_path: Path) -> None:
    save_table(pd.DataFrame([{"metric": "x", "value": 1.0}]), stem="sample", question_dir=tmp_path)

    data = (tmp_path / "artifacts" / "tables" / "sample.csv").read_bytes()
    assert b"\r\n" not in data
    assert data.endswith(b"\n")
