from __future__ import annotations

from pathlib import Path
from typing import Iterable, NamedTuple, Sequence

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


REPORT_DIR: Path = Path(__file__).resolve().parents[1]
PROJECT_DIR: Path = REPORT_DIR.parent
FIG_DIR: Path = REPORT_DIR / "figures"
FONT: str = "SimHeiLocal"
FONT_PATH: Path = Path("C:/Windows/Fonts/simhei.ttf")

FIG_W: float = 330.0
FIG_H: float = 225.0
LEFT: float = 58.0
RIGHT: float = 16.0
BOTTOM: float = 42.0
TOP: float = 22.0
PLOT_W: float = FIG_W - LEFT - RIGHT
PLOT_H: float = FIG_H - BOTTOM - TOP
TICK_FONT: float = 8.2
LABEL_FONT: float = 9.2
LEGEND_FONT: float = 8.0
REF_FONT: float = 7.8

AXIS_COLOR: colors.Color = colors.HexColor("#333333")
GRID_COLOR: colors.Color = colors.HexColor("#d7d7d7")
TEXT_COLOR: colors.Color = colors.HexColor("#222222")
MUTED_COLOR: colors.Color = colors.HexColor("#777777")
BLUE: colors.Color = colors.HexColor("#1b9e77")
ORANGE: colors.Color = colors.HexColor("#d95f02")
PURPLE: colors.Color = colors.HexColor("#7570b3")
GRAY: colors.Color = colors.HexColor("#777777")
RED: colors.Color = colors.HexColor("#c0392b")


class Series(NamedTuple):
    label: str
    x: Sequence[float]
    y: Sequence[float]
    color: colors.Color
    dash: tuple[int, int] | None
    marker: str


class ReferenceLine(NamedTuple):
    value: float
    label: str


class PointItem(NamedTuple):
    label: str
    value: float
    color: colors.Color


def configure_fonts() -> None:
    pdfmetrics.registerFont(TTFont(FONT, str(FONT_PATH)))


def new_canvas(path: Path) -> canvas.Canvas:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_canvas: canvas.Canvas = canvas.Canvas(str(path), pagesize=(FIG_W, FIG_H))
    fig_canvas.setTitle(path.stem)
    fig_canvas.setAuthor("generate_report_figures.py")
    return fig_canvas


def draw_text(
    fig_canvas: canvas.Canvas,
    x: float,
    y: float,
    text: str,
    size: float,
    color: colors.Color,
    align: str,
) -> None:
    fig_canvas.setFillColor(color)
    fig_canvas.setFont(FONT, size)
    if align == "center":
        fig_canvas.drawCentredString(x, y, text)
    elif align == "right":
        fig_canvas.drawRightString(x, y, text)
    else:
        fig_canvas.drawString(x, y, text)


def fmt_tick(value: float) -> str:
    abs_value: float = abs(value)
    if abs_value < 1e-12:
        return "0"
    if abs_value >= 10000:
        return f"{value / 1000:.0f}k"
    if abs_value >= 1000:
        return f"{value:.0f}"
    if abs_value >= 100:
        return f"{value:.0f}"
    if abs_value >= 10:
        return f"{value:.1f}"
    if abs_value >= 1:
        return f"{value:.2f}"
    if abs_value >= 0.01:
        return f"{value:.3f}"
    return f"{value:.1e}"


def as_float_list(values: Sequence[float]) -> list[float]:
    return [float(value) for value in values]


def tick_values(low: float, high: float, count: int) -> list[float]:
    if abs(high - low) < 1e-12:
        return [low]
    return [float(value) for value in np.linspace(low, high, count)]


def map_point(value: float, low: float, high: float, out_low: float, out_high: float) -> float:
    if abs(high - low) < 1e-12:
        return (out_low + out_high) / 2.0
    return out_low + (value - low) / (high - low) * (out_high - out_low)


def padded_range(low: float, high: float, ratio: float) -> tuple[float, float]:
    if abs(high - low) < 1e-12:
        return low - 1.0, high + 1.0
    pad: float = (high - low) * ratio
    return low - pad, high + pad


def data_range(
    series: Sequence[Series],
    x_range: tuple[float, float] | None,
    y_range: tuple[float, float] | None,
) -> tuple[float, float, float, float]:
    xs: list[float] = [value for item in series for value in as_float_list(item.x)]
    ys: list[float] = [value for item in series for value in as_float_list(item.y)]
    raw_x_min, raw_x_max = x_range if x_range is not None else (min(xs), max(xs))
    raw_y_min, raw_y_max = y_range if y_range is not None else (min(ys), max(ys))
    x_min, x_max = (raw_x_min, raw_x_max) if x_range is not None else padded_range(raw_x_min, raw_x_max, 0.02)
    y_min, y_max = (raw_y_min, raw_y_max) if y_range is not None else padded_range(raw_y_min, raw_y_max, 0.06)
    return x_min, x_max, y_min, y_max


def draw_marker(fig_canvas: canvas.Canvas, x: float, y: float, color: colors.Color, marker: str) -> None:
    fig_canvas.setFillColor(color)
    fig_canvas.setStrokeColor(color)
    if marker == "s":
        fig_canvas.rect(x - 2.1, y - 2.1, 4.2, 4.2, stroke=0, fill=1)
    else:
        fig_canvas.circle(x, y, 2.4, stroke=0, fill=1)


def draw_line_axes(
    fig_canvas: canvas.Canvas,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    xlabel: str,
    ylabel: str,
) -> None:
    fig_canvas.setStrokeColor(GRID_COLOR)
    fig_canvas.setLineWidth(0.25)
    for tick in tick_values(x_min, x_max, 4):
        x: float = map_point(tick, x_min, x_max, LEFT, LEFT + PLOT_W)
        fig_canvas.line(x, BOTTOM, x, BOTTOM + PLOT_H)
        draw_text(fig_canvas, x, BOTTOM - 13.0, fmt_tick(tick), TICK_FONT, MUTED_COLOR, "center")
    for tick in tick_values(y_min, y_max, 4):
        y: float = map_point(tick, y_min, y_max, BOTTOM, BOTTOM + PLOT_H)
        fig_canvas.line(LEFT, y, LEFT + PLOT_W, y)
        draw_text(fig_canvas, LEFT - 6.0, y - 3.0, fmt_tick(tick), TICK_FONT, MUTED_COLOR, "right")

    fig_canvas.setStrokeColor(AXIS_COLOR)
    fig_canvas.setLineWidth(0.65)
    fig_canvas.line(LEFT, BOTTOM, LEFT + PLOT_W, BOTTOM)
    fig_canvas.line(LEFT, BOTTOM, LEFT, BOTTOM + PLOT_H)
    draw_text(fig_canvas, LEFT + PLOT_W / 2.0, 8.0, xlabel, LABEL_FONT, TEXT_COLOR, "center")
    fig_canvas.saveState()
    fig_canvas.translate(13.0, BOTTOM + PLOT_H / 2.0)
    fig_canvas.rotate(90)
    draw_text(fig_canvas, 0.0, 0.0, ylabel, LABEL_FONT, TEXT_COLOR, "center")
    fig_canvas.restoreState()


def draw_reference(
    fig_canvas: canvas.Canvas,
    ref: ReferenceLine,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> None:
    if ref.value < y_min or ref.value > y_max:
        return
    y: float = map_point(ref.value, y_min, y_max, BOTTOM, BOTTOM + PLOT_H)
    fig_canvas.setStrokeColor(MUTED_COLOR)
    fig_canvas.setLineWidth(0.7)
    fig_canvas.setDash(3, 2)
    fig_canvas.line(LEFT, y, LEFT + PLOT_W, y)
    fig_canvas.setDash()
    draw_text(fig_canvas, LEFT + PLOT_W - 2.0, y + 3.0, ref.label, REF_FONT, MUTED_COLOR, "right")


def draw_series(
    fig_canvas: canvas.Canvas,
    item: Series,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> None:
    xs: list[float] = as_float_list(item.x)
    ys: list[float] = as_float_list(item.y)
    px: list[float] = [map_point(value, x_min, x_max, LEFT, LEFT + PLOT_W) for value in xs]
    py: list[float] = [map_point(value, y_min, y_max, BOTTOM, BOTTOM + PLOT_H) for value in ys]

    fig_canvas.setStrokeColor(item.color)
    fig_canvas.setLineWidth(1.15)
    if item.dash is not None:
        fig_canvas.setDash(item.dash[0], item.dash[1])
    for index in range(len(px) - 1):
        fig_canvas.line(px[index], py[index], px[index + 1], py[index + 1])
    fig_canvas.setDash()

    stride: int = max(1, len(px) // 7)
    marker_indices: list[int] = list(range(0, len(px), stride))
    if len(px) - 1 not in marker_indices:
        marker_indices.append(len(px) - 1)
    for index in marker_indices:
        draw_marker(fig_canvas, px[index], py[index], item.color, item.marker)


def draw_legend(fig_canvas: canvas.Canvas, series: Sequence[Series]) -> None:
    if len(series) <= 1:
        return
    x0: float = LEFT + 2.0
    y0: float = FIG_H - 13.0
    for index, item in enumerate(series):
        x: float = x0 + 58.0 * index
        fig_canvas.setStrokeColor(item.color)
        fig_canvas.setLineWidth(1.15)
        if item.dash is not None:
            fig_canvas.setDash(item.dash[0], item.dash[1])
        fig_canvas.line(x, y0, x + 18.0, y0)
        fig_canvas.setDash()
        draw_marker(fig_canvas, x + 9.0, y0, item.color, item.marker)
        draw_text(fig_canvas, x + 23.0, y0 - 3.0, item.label, LEGEND_FONT, TEXT_COLOR, "left")


def draw_chart(
    path: Path,
    xlabel: str,
    ylabel: str,
    series: Sequence[Series],
    x_range: tuple[float, float] | None,
    y_range: tuple[float, float] | None,
    reference: ReferenceLine | None,
) -> None:
    fig_canvas: canvas.Canvas = new_canvas(path)
    x_min, x_max, y_min, y_max = data_range(series, x_range, y_range)
    draw_line_axes(fig_canvas, x_min, x_max, y_min, y_max, xlabel, ylabel)
    if reference is not None:
        draw_reference(fig_canvas, reference, x_min, x_max, y_min, y_max)
    for item in series:
        draw_series(fig_canvas, item, x_min, x_max, y_min, y_max)
    draw_legend(fig_canvas, series)
    fig_canvas.save()


def draw_horizontal_point_chart(
    path: Path,
    xlabel: str,
    items: Sequence[PointItem],
    x_range: tuple[float, float],
    reference: ReferenceLine,
) -> None:
    fig_canvas: canvas.Canvas = new_canvas(path)
    x_min, x_max = x_range
    y_min: float = -0.5
    y_max: float = float(len(items)) - 0.5

    fig_canvas.setStrokeColor(GRID_COLOR)
    fig_canvas.setLineWidth(0.25)
    for tick in tick_values(x_min, x_max, 4):
        x: float = map_point(tick, x_min, x_max, LEFT, LEFT + PLOT_W)
        fig_canvas.line(x, BOTTOM, x, BOTTOM + PLOT_H)
        draw_text(fig_canvas, x, BOTTOM - 13.0, fmt_tick(tick), TICK_FONT, MUTED_COLOR, "center")

    x_ref: float = map_point(reference.value, x_min, x_max, LEFT, LEFT + PLOT_W)
    fig_canvas.setStrokeColor(MUTED_COLOR)
    fig_canvas.setLineWidth(0.75)
    fig_canvas.setDash(3, 2)
    fig_canvas.line(x_ref, BOTTOM, x_ref, BOTTOM + PLOT_H)
    fig_canvas.setDash()
    draw_text(fig_canvas, x_ref + 3.0, FIG_H - 15.0, reference.label, REF_FONT, MUTED_COLOR, "left")

    fig_canvas.setStrokeColor(AXIS_COLOR)
    fig_canvas.setLineWidth(0.65)
    fig_canvas.line(LEFT, BOTTOM, LEFT + PLOT_W, BOTTOM)
    fig_canvas.line(LEFT, BOTTOM, LEFT, BOTTOM + PLOT_H)
    draw_text(fig_canvas, LEFT + PLOT_W / 2.0, 8.0, xlabel, LABEL_FONT, TEXT_COLOR, "center")

    for index, item in enumerate(items):
        y: float = map_point(float(index), y_min, y_max, BOTTOM, BOTTOM + PLOT_H)
        x: float = map_point(item.value, x_min, x_max, LEFT, LEFT + PLOT_W)
        fig_canvas.setStrokeColor(GRID_COLOR)
        fig_canvas.setLineWidth(0.5)
        fig_canvas.line(LEFT, y, x, y)
        fig_canvas.setStrokeColor(item.color)
        fig_canvas.setFillColor(item.color)
        fig_canvas.circle(x, y, 3.0, stroke=0, fill=1)
        draw_text(fig_canvas, LEFT - 7.0, y - 3.3, item.label, TICK_FONT, TEXT_COLOR, "right")
        draw_text(fig_canvas, x + 6.0, y - 3.0, fmt_tick(item.value), TICK_FONT, item.color, "left")
    fig_canvas.save()


def make_q1_figures() -> None:
    speed: pd.DataFrame = pd.read_csv(PROJECT_DIR / "artifacts/q1/data/constant_speed_profile.csv")
    mach: pd.DataFrame = pd.read_csv(PROJECT_DIR / "artifacts/q1/data/constant_mach_profile.csv")
    comparison: pd.DataFrame = pd.read_csv(PROJECT_DIR / "artifacts/q1/data/strategy_comparison.csv")
    x_max: float = float(max(speed["time_s"].max(), mach["time_s"].max()))
    mass_min: float = float(min(speed["mass_kg"].min(), mach["mass_kg"].min()))
    mass_max: float = float(max(speed["mass_kg"].max(), mach["mass_kg"].max()))

    draw_chart(
        FIG_DIR / "fig_q1_closure_mass_height.pdf",
        "质量 / kg",
        "高度 / m",
        [
            Series("等速", speed["mass_kg"].tolist(), speed["height_m"].tolist(), BLUE, None, "o"),
            Series("等马赫", mach["mass_kg"].tolist(), mach["height_m"].tolist(), ORANGE, (4, 2), "s"),
        ],
        (mass_min, mass_max),
        None,
        None,
    )
    draw_chart(
        FIG_DIR / "fig_q1_closure_speed_mach.pdf",
        "质量 / kg",
        "马赫数",
        [
            Series("等速", speed["mass_kg"].tolist(), speed["mach"].tolist(), BLUE, None, "o"),
            Series("等马赫", mach["mass_kg"].tolist(), mach["mach"].tolist(), ORANGE, (4, 2), "s"),
        ],
        (mass_min, mass_max),
        None,
        None,
    )
    draw_chart(
        FIG_DIR / "fig_q1_height_time.pdf",
        "时间 / s",
        "高度 / m",
        [
            Series("等速", speed["time_s"].tolist(), speed["height_m"].tolist(), BLUE, None, "o"),
            Series("等马赫", mach["time_s"].tolist(), mach["height_m"].tolist(), ORANGE, (4, 2), "s"),
        ],
        (0.0, x_max),
        None,
        None,
    )
    draw_chart(
        FIG_DIR / "fig_q1_climb_time.pdf",
        "时间 / s",
        "爬升率 / (m/s)",
        [
            Series("等速", speed["time_s"].tolist(), speed["climb_rate_mps"].tolist(), BLUE, None, "o"),
            Series("等马赫", mach["time_s"].tolist(), mach["climb_rate_mps"].tolist(), ORANGE, (4, 2), "s"),
        ],
        (0.0, x_max),
        None,
        None,
    )

    row_speed: pd.Series = comparison.loc[comparison["strategy"] == "constant_speed"].iloc[0]
    row_mach: pd.Series = comparison.loc[comparison["strategy"] == "constant_mach"].iloc[0]
    items: list[PointItem] = [
        PointItem("爬升率", float(row_mach["mean_climb_rate_mps"] / row_speed["mean_climb_rate_mps"]), GRAY),
        PointItem("顺风", float(row_mach["wind_distance_contribution_m"] / row_speed["wind_distance_contribution_m"]), PURPLE),
        PointItem("航程", float(row_mach["final_distance_m"] / row_speed["final_distance_m"]), ORANGE),
        PointItem("时间", float(row_mach["final_time_s"] / row_speed["final_time_s"]), BLUE),
    ]
    draw_horizontal_point_chart(
        FIG_DIR / "fig_q1_metrics_bar.pdf",
        "等马赫 / 等速",
        items,
        (0.70, 1.10),
        ReferenceLine(1.0, "等速基准"),
    )


def make_q2_figures() -> None:
    standard: pd.DataFrame = pd.read_csv(PROJECT_DIR / "artifacts/q2/data/q2_standard_isa_profile.csv")
    warm: pd.DataFrame = pd.read_csv(PROJECT_DIR / "artifacts/q2/data/q2_temperature_corrected_profile.csv")
    temp: pd.DataFrame = pd.read_csv(PROJECT_DIR / "artifacts/q2/data/q2_temperature_sensitivity.csv")
    x_max: float = float(max(standard["distance_m"].max(), warm["distance_m"].max()) / 1000.0)

    draw_chart(
        FIG_DIR / "fig_q2_density_path.pdf",
        "航程 / km",
        "密度 / (kg/m³)",
        [
            Series("ISA", (standard["distance_m"] / 1000.0).tolist(), standard["density_kgm3"].tolist(), BLUE, None, "o"),
            Series("+10K", (warm["distance_m"] / 1000.0).tolist(), warm["density_kgm3"].tolist(), ORANGE, (4, 2), "s"),
        ],
        (0.0, x_max),
        None,
        None,
    )
    draw_chart(
        FIG_DIR / "fig_q2_aero_path.pdf",
        "航程 / km",
        "马赫数",
        [
            Series("ISA", (standard["distance_m"] / 1000.0).tolist(), standard["mach"].tolist(), BLUE, None, "o"),
            Series("+10K", (warm["distance_m"] / 1000.0).tolist(), warm["mach"].tolist(), ORANGE, (4, 2), "s"),
        ],
        (0.0, x_max),
        None,
        None,
    )
    draw_chart(
        FIG_DIR / "fig_q2_fuel_rate.pdf",
        "航程 / km",
        "油流 / (kg/s)",
        [
            Series("ISA", (standard["distance_m"] / 1000.0).tolist(), standard["fuel_flow_kgs"].tolist(), BLUE, None, "o"),
            Series("+10K", (warm["distance_m"] / 1000.0).tolist(), warm["fuel_flow_kgs"].tolist(), ORANGE, (4, 2), "s"),
        ],
        (0.0, x_max),
        None,
        None,
    )
    draw_chart(
        FIG_DIR / "fig_q2_temp_fuel.pdf",
        "温差 / K",
        "油耗变化 / %",
        [Series("油耗变化", temp["temperature_offset_k"].tolist(), temp["fuel_delta_vs_standard_pct"].tolist(), BLUE, None, "o")],
        (-10.0, 10.0),
        None,
        ReferenceLine(0.0, "ISA"),
    )
    draw_chart(
        FIG_DIR / "fig_q2_temp_mass.pdf",
        "温差 / K",
        "终点质量 / kg",
        [Series("终点质量", temp["temperature_offset_k"].tolist(), temp["final_mass_kg"].tolist(), ORANGE, None, "o")],
        (-10.0, 10.0),
        None,
        ReferenceLine(62000.0, "下限"),
    )


def make_q3_figures() -> None:
    final_traj: pd.DataFrame = pd.read_csv(PROJECT_DIR / "questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv")
    validation: pd.DataFrame = pd.read_csv(PROJECT_DIR / "questions/q3/artifacts/tables/no_wind_final_optimal_validation.csv")
    final_x_max: float = float(final_traj["distance_m"].max() / 1000.0)
    draw_chart(
        FIG_DIR / "fig_q3_final_height_path.pdf",
        "航程 / km",
        "高度 / m",
        [Series("最终无风", (final_traj["distance_m"] / 1000.0).tolist(), final_traj["height_m"].tolist(), BLUE, None, "o")],
        (0.0, final_x_max),
        None,
        ReferenceLine(12000.0, "上界"),
    )
    draw_chart(
        FIG_DIR / "fig_q3_final_mass_path.pdf",
        "航程 / km",
        "质量 / kg",
        [Series("最终无风", (final_traj["distance_m"] / 1000.0).tolist(), final_traj["mass_kg"].tolist(), ORANGE, None, "o")],
        (0.0, final_x_max),
        None,
        ReferenceLine(62000.0, "下限"),
    )
    draw_chart(
        FIG_DIR / "fig_q3_final_thrust_path.pdf",
        "航程 / km",
        "推力 / kN",
        [Series("最终无风", (final_traj["distance_m"] / 1000.0).tolist(), (final_traj["thrust_n"] / 1000.0).tolist(), BLUE, None, "o")],
        (0.0, final_x_max),
        None,
        None,
    )
    gamma_deg: list[float] = (final_traj["gamma_rad"] * 180.0 / np.pi).tolist()
    draw_chart(
        FIG_DIR / "fig_q3_final_gamma_path.pdf",
        "航程 / km",
        "航迹角 / deg",
        [Series("最终无风", (final_traj["distance_m"] / 1000.0).tolist(), gamma_deg, ORANGE, None, "o")],
        (0.0, final_x_max),
        None,
        ReferenceLine(0.0, "平飞"),
    )

    row: pd.Series = validation.iloc[0]
    items: list[PointItem] = [
        PointItem("初值", float(np.log10(row["multi_initial_objective_range_kg"] / 1.0)), RED),
        PointItem("网格", float(np.log10(row["objective_grid_abs_delta_kg"] / 1.0)), GRAY),
        PointItem("燃油", float(np.log10(row["fuel_identity_residual_kg"] / 5e-2)), PURPLE),
        PointItem("高度", float(np.log10(row["reintegration_terminal_height_error_m"] / 1e-1)), ORANGE),
        PointItem("速度", float(np.log10(row["reintegration_terminal_speed_error_mps"] / 1e-3)), BLUE),
    ]
    draw_horizontal_point_chart(
        FIG_DIR / "fig_q3_validation_summary.pdf",
        "log10(残差/阈值)",
        items,
        (-4.0, 0.4),
        ReferenceLine(0.0, "阈值"),
    )


def verify_outputs(names: Iterable[str]) -> None:
    missing: list[str] = [name for name in names if not (FIG_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"missing figures: {missing}")


def main() -> None:
    configure_fonts()
    make_q1_figures()
    make_q2_figures()
    make_q3_figures()
    verify_outputs(
        [
            "fig_q1_closure_mass_height.pdf",
            "fig_q1_closure_speed_mach.pdf",
            "fig_q1_height_time.pdf",
            "fig_q1_climb_time.pdf",
            "fig_q1_metrics_bar.pdf",
            "fig_q2_density_path.pdf",
            "fig_q2_aero_path.pdf",
            "fig_q2_fuel_rate.pdf",
            "fig_q2_temp_fuel.pdf",
            "fig_q2_temp_mass.pdf",
            "fig_q3_final_height_path.pdf",
            "fig_q3_final_mass_path.pdf",
            "fig_q3_final_thrust_path.pdf",
            "fig_q3_final_gamma_path.pdf",
            "fig_q3_validation_summary.pdf",
        ]
    )


if __name__ == "__main__":
    main()
