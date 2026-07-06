from pathlib import Path


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
