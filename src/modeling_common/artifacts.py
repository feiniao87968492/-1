from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pandas as pd
from matplotlib.figure import Figure


def _as_dataframe(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, pd.Series):
        return data.rename(data.name or "value").reset_index()
    try:
        return pd.DataFrame(data)
    except Exception as exc:  # noqa: BLE001
        raise TypeError("Figure data must be convertible to a pandas DataFrame") from exc


def save_figure_bundle(
    *,
    fig: Figure,
    data: Any,
    stem: str,
    question_dir: str | Path,
    title: str,
    source_script: str,
    notes: str = "",
    dpi: int = 300,
) -> dict[str, Path]:
    """Save a figure, its source data, and metadata using the same stable stem."""
    if not stem or any(ch in stem for ch in " /\\"):
        raise ValueError("stem must be a non-empty filename-safe identifier")

    qdir = Path(question_dir)
    figure_dir = qdir / "artifacts" / "figures"
    data_dir = qdir / "artifacts" / "figure_data"
    figure_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    frame = _as_dataframe(data)
    if frame.empty:
        raise ValueError("Refusing to save a paper-level figure without source data")

    figure_path = figure_dir / f"{stem}.png"
    data_path = data_dir / f"{stem}.csv"
    metadata_path = data_dir / f"{stem}.meta.json"

    fig.savefig(figure_path, dpi=dpi, bbox_inches="tight")
    frame.to_csv(data_path, index=False, lineterminator="\n")
    metadata = {
        "stem": stem,
        "title": title,
        "source_script": source_script,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rows": int(frame.shape[0]),
        "columns": list(map(str, frame.columns)),
        "notes": notes,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"figure": figure_path, "data": data_path, "metadata": metadata_path}


def save_table(
    data: Any,
    *,
    stem: str,
    question_dir: str | Path,
    index: bool = False,
    save_xlsx: bool = False,
) -> dict[str, Path]:
    """Save a result table in machine-readable formats."""
    frame = _as_dataframe(data)
    if frame.empty:
        raise ValueError("Refusing to save an empty result table")

    table_dir = Path(question_dir) / "artifacts" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    csv_path = table_dir / f"{stem}.csv"
    frame.to_csv(csv_path, index=index, lineterminator="\n")
    outputs = {"csv": csv_path}
    if save_xlsx:
        xlsx_path = table_dir / f"{stem}.xlsx"
        frame.to_excel(xlsx_path, index=index)
        outputs["xlsx"] = xlsx_path
    return outputs
