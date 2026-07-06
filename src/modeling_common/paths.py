from __future__ import annotations

from pathlib import Path


def project_root(start: Path | None = None) -> Path:
    """Locate the repository root by searching for AGENTS.md and pyproject.toml."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "AGENTS.md").exists() and (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError("Could not locate project root from current path")
