from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import math

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


REPORT_DIR: Path = Path(__file__).resolve().parents[1]
PROJECT_DIR: Path = REPORT_DIR.parent
FIG_DIR: Path = REPORT_DIR / "figures"
FONT: str = "SimHei"
FONT_PATH: Path = Path("C:/Windows/Fonts/simhei.ttf")

W: float = 620.0
H: float = 390.0
BLUE = colors.HexColor("#1f78b4")
ORANGE = colors.HexColor("#e66101")
GREEN = colors.HexColor("#1b9e77")
PURPLE = colors.HexColor("#756bb1")
RED = colors.HexColor("#c0392b")
GRAY = colors.HexColor("#6f6f6f")
LIGHT_GRAY = colors.HexColor("#e7e9ee")
TEXT = colors.HexColor("#242424")


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Line:
    label: str
    x: list[float]
    y: list[float]
    color: colors.Color
    width: float
    dash: tuple[int, int] | None


def configure() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont(FONT, str(FONT_PATH)))


def cnv(path: Path) -> canvas.Canvas:
    c = canvas.Canvas(str(path), pagesize=(W, H))
    c.setTitle(path.stem)
    c.setAuthor("generate_paper_figures_v2.py")
    return c


def text(c: canvas.Canvas, x: float, y: float, s: str, size: float, color: colors.Color = TEXT, align: str = "left") -> None:
    c.setFont(FONT, size)
    c.setFillColor(color)
    if align == "center":
        c.drawCentredString(x, y, s)
    elif align == "right":
        c.drawRightString(x, y, s)
    else:
        c.drawString(x, y, s)


def fmt(v: float) -> str:
    av = abs(v)
    if av < 1e-12:
        return "0"
    if av >= 10000:
        return f"{v/1000:.0f}k"
    if av >= 1000:
        return f"{v:.0f}"
    if av >= 100:
        return f"{v:.0f}"
    if av >= 10:
        return f"{v:.1f}"
    if av >= 1:
        return f"{v:.2f}"
    if av >= 0.01:
        return f"{v:.3f}"
    return f"{v:.1e}"


def mapv(v: float, lo: float, hi: float, a: float, b: float) -> float:
    if abs(hi - lo) < 1e-12:
        return (a + b) / 2
    return a + (v - lo) / (hi - lo) * (b - a)


def pad(lo: float, hi: float, r: float) -> tuple[float, float]:
    if abs(hi - lo) < 1e-12:
        return lo - 1, hi + 1
    p = (hi - lo) * r
    return lo - p, hi + p


def axes(c: canvas.Canvas, box: Box, xlo: float, xhi: float, ylo: float, yhi: float, xlabel: str, ylabel: str) -> None:
    c.setStrokeColor(LIGHT_GRAY)
    c.setLineWidth(0.35)
    for tick in np.linspace(xlo, xhi, 3):
        x = mapv(float(tick), xlo, xhi, box.x, box.x + box.w)
        c.line(x, box.y, x, box.y + box.h)
        text(c, x, box.y - 18, fmt(float(tick)), 12, GRAY, "center")
    for tick in np.linspace(ylo, yhi, 3):
        y = mapv(float(tick), ylo, yhi, box.y, box.y + box.h)
        c.line(box.x, y, box.x + box.w, y)
        text(c, box.x - 9, y - 4, fmt(float(tick)), 12, GRAY, "right")
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(0.8)
    c.line(box.x, box.y, box.x + box.w, box.y)
    c.line(box.x, box.y, box.x, box.y + box.h)
    text(c, box.x + box.w / 2, box.y - 41, xlabel, 14, TEXT, "center")
    c.saveState()
    c.translate(box.x - 52, box.y + box.h / 2)
    c.rotate(90)
    text(c, 0, 0, ylabel, 14, TEXT, "center")
    c.restoreState()


def horizontal_axes(c: canvas.Canvas, box: Box, xlo: float, xhi: float, xlabel: str) -> None:
    c.setStrokeColor(LIGHT_GRAY)
    c.setLineWidth(0.35)
    for tick in np.linspace(xlo, xhi, 3):
        x = mapv(float(tick), xlo, xhi, box.x, box.x + box.w)
        c.line(x, box.y, x, box.y + box.h)
        text(c, x, box.y - 18, fmt(float(tick)), 12, GRAY, "center")
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(0.8)
    c.line(box.x, box.y, box.x + box.w, box.y)
    c.line(box.x, box.y, box.x, box.y + box.h)
    text(c, box.x + box.w / 2, box.y - 41, xlabel, 14, TEXT, "center")


def legend(c: canvas.Canvas, items: list[tuple[str, colors.Color]], x: float, y: float) -> None:
    for i, (label, color) in enumerate(items):
        yy = y - i * 21
        c.setFillColor(color)
        c.circle(x, yy + 4, 4.5, stroke=0, fill=1)
        text(c, x + 12, yy, label, 12.5, TEXT)


def line_chart(
    path: Path,
    title: str,
    lines: list[Line],
    xlabel: str,
    ylabel: str,
    note: str,
    ref_y: tuple[float, str] | None = None,
    x_range: tuple[float, float] | None = None,
    y_range: tuple[float, float] | None = None,
    x_nonneg: bool = False,
) -> None:
    c = cnv(path)
    box = Box(82, 74, 430, 275)
    xs = [v for line in lines for v in line.x]
    ys = [v for line in lines for v in line.y]
    xlo, xhi = x_range if x_range else pad(min(xs), max(xs), 0.02)
    ylo, yhi = y_range if y_range else pad(min(ys), max(ys), 0.08)
    if x_nonneg:
        xlo = max(0, xlo)
    if ref_y is not None:
        ylo = min(ylo, ref_y[0])
        yhi = max(yhi, ref_y[0])
        ylo, yhi = pad(ylo, yhi, 0.04)
    axes(c, box, xlo, xhi, ylo, yhi, xlabel, ylabel)
    if ref_y is not None:
        y = mapv(ref_y[0], ylo, yhi, box.y, box.y + box.h)
        c.setDash(4, 3)
        c.setStrokeColor(GRAY)
        c.line(box.x, y, box.x + box.w, y)
        c.setDash()
        text(c, box.x + box.w - 4, y + 6, ref_y[1], 11, GRAY, "right")
    for line in lines:
        pts = [(mapv(x, xlo, xhi, box.x, box.x + box.w), mapv(y, ylo, yhi, box.y, box.y + box.h)) for x, y in zip(line.x, line.y)]
        c.setStrokeColor(line.color)
        c.setLineWidth(line.width)
        if line.dash:
            c.setDash(*line.dash)
        p = c.beginPath()
        p.moveTo(pts[0][0], pts[0][1])
        for x, y in pts[1:]:
            p.lineTo(x, y)
        c.drawPath(p, stroke=1, fill=0)
        c.setDash()
        c.setFillColor(line.color)
        step = max(1, len(pts) // 12)
        for x, y in pts[::step]:
            c.circle(x, y, 2.4, stroke=0, fill=1)
    legend(c, [(line.label, line.color) for line in lines], 535, 330)
    c.showPage()
    c.save()


def horizontal_bar(path: Path, title: str, labels: list[str], values: list[float], colors_: list[colors.Color], xlabel: str, note: str, ref: float | None = None, x_nonneg: bool = False) -> None:
    c = cnv(path)
    box = Box(170, 80, 350, 260)
    lo = min(0, min(values), ref if ref is not None else 0)
    hi = max(values + ([ref] if ref is not None else [0]))
    lo, hi = pad(lo, hi, 0.14)
    if x_nonneg:
        lo = max(0, lo)
    horizontal_axes(c, box, lo, hi, xlabel)
    if ref is not None:
        x = mapv(ref, lo, hi, box.x, box.x + box.w)
        c.setStrokeColor(GRAY)
        c.setDash(4, 3)
        c.line(x, box.y, x, box.y + box.h)
        c.setDash()
    for i, (lab, val, col) in enumerate(zip(labels, values, colors_)):
        y = mapv(i, -0.5, len(labels) - 0.5, box.y, box.y + box.h)
        x0 = mapv(0, lo, hi, box.x, box.x + box.w)
        x1 = mapv(val, lo, hi, box.x, box.x + box.w)
        c.setFillColor(col)
        c.rect(min(x0, x1), y - 8, abs(x1 - x0), 16, stroke=0, fill=1)
        text(c, box.x - 12, y - 5, lab, 12, TEXT, "right")
        text(c, max(x0, x1) + 7, y - 5, f"{val:.3f}", 11.5, col)
    c.showPage()
    c.save()


def grouped_bar(path: Path, title: str, groups: list[str], series: list[tuple[str, list[float], colors.Color]], ylabel: str, note: str) -> None:
    c = cnv(path)
    box = Box(86, 84, 410, 260)
    vals = [v for _, arr, _ in series for v in arr]
    ylo, yhi = pad(min(0, min(vals)), max(vals), 0.1)
    axes(c, box, -0.5, len(groups) - 0.5, ylo, yhi, "", ylabel)
    width = 0.18
    for si, (name, arr, col) in enumerate(series):
        for gi, val in enumerate(arr):
            cx = gi + (si - (len(series) - 1) / 2) * width * 1.5
            x0 = mapv(cx - width / 2, -0.5, len(groups) - 0.5, box.x, box.x + box.w)
            x1 = mapv(cx + width / 2, -0.5, len(groups) - 0.5, box.x, box.x + box.w)
            y0 = mapv(0, ylo, yhi, box.y, box.y + box.h)
            y1 = mapv(val, ylo, yhi, box.y, box.y + box.h)
            c.setFillColor(col)
            c.rect(x0, min(y0, y1), x1 - x0, abs(y1 - y0), stroke=0, fill=1)
    for gi, g in enumerate(groups):
        x = mapv(gi, -0.5, len(groups) - 0.5, box.x, box.x + box.w)
        text(c, x, box.y - 19, g, 12, GRAY, "center")
    legend(c, [(name, col) for name, _, col in series], 522, 330)
    c.showPage()
    c.save()


def read_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(PROJECT_DIR / path)


def fig_q1() -> None:
    speed = read_csv("artifacts/q1/data/constant_speed_profile.csv")
    mach = read_csv("artifacts/q1/data/constant_mach_profile.csv")
    comp = read_csv("artifacts/q1/data/strategy_comparison.csv")
    line_chart(
        FIG_DIR / "fig_v2_q1_closure_mechanism.pdf",
        "问题一：升力平衡闭合如何决定爬升高度",
        [
            Line("等速", speed["mass_kg"].tolist(), speed["height_m"].tolist(), BLUE, 2.4, None),
            Line("等马赫", mach["mass_kg"].tolist(), mach["height_m"].tolist(), ORANGE, 2.4, None),
        ],
        "质量 / kg",
        "高度 / m",
        "同一终止质量下，两种经验策略因速度闭合不同而得到不同高度轨迹",
        x_nonneg=True,
    )
    line_chart(
        FIG_DIR / "fig_v2_q1_height_time.pdf",
        "问题一：高度--时间剖面对比",
        [
            Line("等速", speed["time_s"].tolist(), speed["height_m"].tolist(), BLUE, 2.4, None),
            Line("等马赫", mach["time_s"].tolist(), mach["height_m"].tolist(), ORANGE, 2.4, None),
        ],
        "时间 / s",
        "高度 / m",
        "等速策略爬升更快、终点高度更高；等马赫策略飞行时间更长",
        x_nonneg=True,
    )
    line_chart(
        FIG_DIR / "fig_v2_q1_climb_rate.pdf",
        "问题一：爬升率随时间变化",
        [
            Line("等速", speed["time_s"].tolist(), speed["climb_rate_mps"].tolist(), BLUE, 2.4, None),
            Line("等马赫", mach["time_s"].tolist(), mach["climb_rate_mps"].tolist(), ORANGE, 2.4, None),
        ],
        "时间 / s",
        "爬升率 / (m/s)",
        "爬升率差异解释了两类策略在时间和高度上的分化",
        x_nonneg=True,
    )
    cs = comp.loc[comp["strategy"] == "constant_speed"].iloc[0]
    cm = comp.loc[comp["strategy"] == "constant_mach"].iloc[0]
    labels = ["时间", "地面航程", "顺风贡献", "平均爬升率"]
    ratios = [
        cm["final_time_s"] / cs["final_time_s"] - 1,
        cm["final_distance_m"] / cs["final_distance_m"] - 1,
        cm["wind_distance_contribution_m"] / cs["wind_distance_contribution_m"] - 1,
        cm["mean_climb_rate_mps"] / cs["mean_climb_rate_mps"] - 1,
    ]
    horizontal_bar(
        FIG_DIR / "fig_v2_q1_metric_comparison.pdf",
        "问题一：等马赫相对等速的工程指标变化",
        labels,
        [v * 100 for v in ratios],
        [ORANGE if v >= 0 else BLUE for v in ratios],
        "相对变化 / %",
        "油耗相同后，比较重点转向航程、时间和爬升结构",
        0,
    )


def fig_q2() -> None:
    atm = read_csv("questions/q2/artifacts/figure_data/atmosphere_path.csv")
    fuel = read_csv("questions/q2/artifacts/figure_data/fuel_rate_path.csv")
    sens = read_csv("questions/q2/artifacts/figure_data/temperature_sensitivity.csv")
    std = atm.loc[atm["scenario"] == "standard_isa"]
    plus = atm.loc[atm["scenario"] == "temp_plus_10K"]
    line_chart(
        FIG_DIR / "fig_v2_q2_density_correction.pdf",
        "问题二：温差修正改变沿程密度",
        [
            Line("标准 ISA", (std["distance_m"] / 1000).tolist(), std["density_kgm3"].tolist(), BLUE, 2.4, None),
            Line("+10K 修正", (plus["distance_m"] / 1000).tolist(), plus["density_kgm3"].tolist(), ORANGE, 2.4, None),
        ],
        "航程 / km",
        "密度 / (kg/m³)",
        "温差通过静力平衡传递到密度，而非只改变温度本身",
        x_nonneg=True,
    )
    line_chart(
        FIG_DIR / "fig_v2_q2_sound_speed_correction.pdf",
        "问题二：温差修正改变声速诊断",
        [
            Line("标准 ISA", (std["distance_m"] / 1000).tolist(), std["sound_speed_mps"].tolist(), BLUE, 2.4, None),
            Line("+10K 修正", (plus["distance_m"] / 1000).tolist(), plus["sound_speed_mps"].tolist(), ORANGE, 2.4, None),
        ],
        "航程 / km",
        "声速 / (m/s)",
        "声速变化进一步影响马赫数、升力系数和阻力计算",
        x_nonneg=True,
    )
    fstd = fuel.loc[fuel["scenario"] == "standard_isa"].sort_values("distance_m")
    fplus = fuel.loc[fuel["scenario"] == "temp_plus_10K"].sort_values("distance_m")
    common_x = fstd["distance_m"].to_numpy()
    delta = np.interp(common_x, fplus["distance_m"], fplus["cumulative_fuel_path_kg"]) - fstd["cumulative_fuel_path_kg"].to_numpy()
    line_chart(
        FIG_DIR / "fig_v2_q2_fuel_accumulation.pdf",
        "问题二：22.744 kg 油耗差如何沿程累积",
        [Line("+10K 累计差", (common_x / 1000).tolist(), delta.tolist(), ORANGE, 2.5, None)],
        "航程 / km",
        "累计油耗差 / kg",
        "全程小幅燃油率差异在终点累积为 22.744 kg",
        ref_y=(22.744, "终点 22.744 kg"),
        x_nonneg=True,
    )
    line_chart(
        FIG_DIR / "fig_v2_q2_temperature_sensitivity.pdf",
        "问题二：常温偏差对总油耗的灵敏度",
        [Line("油耗变化", sens["temperature_offset_k"].tolist(), sens["fuel_delta_vs_standard_pct"].tolist(), PURPLE, 2.5, None)],
        "温差 / K",
        "相对 ISA 变化 / %",
        "|ΔT|≤10K 时，总油耗变化小于 0.3%",
        ref_y=(0, "标准 ISA"),
    )


def fig_q3() -> None:
    base = read_csv("questions/q3/artifacts/tables/baseline_feasibility.csv")
    result = read_csv("questions/q3/artifacts/tables/no_wind_final_optimal_results.csv").iloc[0]
    traj = read_csv("questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv")
    val = read_csv("questions/q3/artifacts/tables/no_wind_final_optimal_validation.csv").iloc[0]
    diag = read_csv("questions/q3/artifacts/tables/no_wind_final_optimal_diagnostics.csv")
    hmax = read_csv("questions/q3/artifacts/tables/no_wind_final_hmax_sensitivity.csv")
    labels = ["有风固定路径", "无风固定路径", "无风最终优化"]
    values = [
        float(base.loc[base["wind_model"] == "configured_wind", "final_mass_kg"].iloc[0]),
        float(base.loc[base["wind_model"] == "no_wind", "final_mass_kg"].iloc[0]),
        float(result["terminal_mass_kg"]),
    ]
    horizontal_bar(
        FIG_DIR / "fig_v2_q3_feasibility_bridge.pdf",
        "问题三：为什么需要重新优化无风轨迹",
        labels,
        values,
        [GREEN, RED, GREEN],
        "终端质量 / kg",
        "无风固定路径低于 62000 kg 下限，最终优化恢复可行余量",
        62000,
        x_nonneg=True,
    )
    line_chart(
        FIG_DIR / "fig_v2_q3_state_corridor_height.pdf",
        "问题三：无风最终优化高度走廊",
        [Line("高度", (traj["distance_m"] / 1000).tolist(), traj["height_m"].tolist(), PURPLE, 2.4, None)],
        "航程 / km",
        "高度 / m",
        "轨迹中段贴近 12000 m 上界，体现高度约束活跃",
        ref_y=(12000, "高度上界"),
        x_nonneg=True,
    )
    line_chart(
        FIG_DIR / "fig_v2_q3_state_corridor_mass.pdf",
        "问题三：无风最终优化质量余量",
        [Line("质量", (traj["distance_m"] / 1000).tolist(), traj["mass_kg"].tolist(), ORANGE, 2.4, None)],
        "航程 / km",
        "质量 / kg",
        "终端质量 62107.186 kg，高于 62000 kg 下限",
        ref_y=(62000, "质量下限"),
        x_nonneg=True,
    )
    line_chart(
        FIG_DIR / "fig_v2_q3_control_schedule.pdf",
        "问题三：最终优化控制量调度",
        [
            Line("推力/kN", (traj["distance_m"] / 1000).tolist(), (traj["thrust_n"] / 1000).tolist(), BLUE, 2.3, None),
            Line("航迹角×10", (traj["distance_m"] / 1000).tolist(), (traj["gamma_rad"] * 180 / math.pi * 10).tolist(), ORANGE, 2.1, (4, 2)),
        ],
        "航程 / km",
        "推力 kN / 航迹角×10",
        "推力未贴近零推力边界，航迹角保持小角度变化",
        x_nonneg=True,
    )
    stable = diag.loc[(diag["initial_guess"] == "gate2") & (diag["final_nodes"].isin([61, 121, 241]))].sort_values("final_nodes")
    line_chart(
        FIG_DIR / "fig_v2_q3_grid_stability.pdf",
        "问题三：最终油耗对网格加密保持稳定",
        [Line("总油耗", stable["final_nodes"].tolist(), stable["fuel_used_kg"].tolist(), GREEN, 2.4, None)],
        "节点数 N",
        "总油耗 / kg",
        "N=61、121、241 三层网格均稳定在 10342.81 kg 附近",
        x_nonneg=True,
    )
    metrics = [
        ("速度", math.log10(float(val["reintegration_terminal_speed_error_mps"]) / 1e-3)),
        ("高度", math.log10(float(val["reintegration_terminal_height_error_m"]) / 1e-1)),
        ("燃油", math.log10(float(val["fuel_identity_residual_kg"]) / 5e-2)),
        ("网格", math.log10(float(val["objective_grid_abs_delta_kg"]) / 1.0)),
    ]
    horizontal_bar(
        FIG_DIR / "fig_v2_q3_validation_dashboard.pdf",
        "问题三：q3-T08 验证残差均低于阈值",
        [m[0] for m in metrics],
        [m[1] for m in metrics],
        [GREEN] * len(metrics),
        "log10(残差/阈值)",
        "0 为阈值线，负值表示通过",
        0,
    )


def fig_q4() -> None:
    comp = read_csv("questions/q4/artifacts/tables/strategy_comparison.csv")
    traj = read_csv("questions/q4/artifacts/tables/wind_optimal_trajectory.csv")
    height = read_csv("questions/q4/artifacts/figure_data/height_range_comparison.csv")
    beta = read_csv("questions/q4/artifacts/tables/beta_sensitivity.csv")
    rng = read_csv("questions/q4/artifacts/tables/fixed_fuel_range_trials.csv")
    res = read_csv("questions/q4/artifacts/tables/wind_optimal_results.csv").iloc[0]
    labels = comp["strategy"].map({"constant_speed_baseline": "等速基线", "configured_wind_optimal": "有风局部优化"}).tolist()
    grouped_bar(
        FIG_DIR / "fig_v2_q4_strategy_savings.pdf",
        "问题四：固定共同航程下的燃油对比",
        labels,
        [("总油耗", comp["fuel_used_kg"].tolist(), BLUE)],
        "燃油 / kg",
        "有风局部优化比等速基线节省 563.416 kg（5.403%）",
    )
    lines = []
    for name, color in [("q1_constant_speed", BLUE), ("configured_wind_optimal", ORANGE)]:
        sub = height.loc[height["strategy"] == name].sort_values("distance_m")
        if len(sub) > 0:
            lines.append(Line("等速基线" if name == "q1_constant_speed" else "有风优化", (sub["distance_m"] / 1000).tolist(), sub["height_m"].tolist(), color, 2.3, None))
    line_chart(
        FIG_DIR / "fig_v2_q4_height_profile_compare.pdf",
        "问题四：有风优化与等速基线高度剖面对比",
        lines,
        "航程 / km",
        "高度 / m",
        "有风优化中段较低、末段回到终端高度约束附近",
        x_nonneg=True,
    )
    line_chart(
        FIG_DIR / "fig_v2_q4_control_profile.pdf",
        "问题四：有风局部优化速度与推力剖面",
        [
            Line("空速", (traj["distance_m"] / 1000).tolist(), traj["airspeed_mps"].tolist(), BLUE, 2.4, None),
            Line("推力/200", (traj["distance_m"] / 1000).tolist(), (traj["thrust_n"] / 200).tolist(), ORANGE, 2.2, (4, 2)),
        ],
        "航程 / km",
        "空速 / 推力缩放",
        "低维控制下推力调度平稳，速度先降后回到终端值",
        x_nonneg=True,
    )
    horizontal_bar(
        FIG_DIR / "fig_v2_q4_fixed_fuel_range.pdf",
        "问题四：固定燃油预算下的航程下界",
        [f"{v:.2f}×" for v in rng["range_factor"].tolist()] if "range_factor" in rng.columns else [str(i + 1) for i in range(len(rng))],
        (rng["target_distance_m"] / 1000).tolist() if "target_distance_m" in rng.columns else (rng.iloc[:, 1] / 1000).tolist(),
        [GREEN] * len(rng),
        "试验航程 / km",
        "1.06 倍航程仍预算内，因此 201.168 km 为下界估计",
        x_nonneg=True,
    )
    line_chart(
        FIG_DIR / "fig_v2_q4_beta_sensitivity.pdf",
        "问题四：β 扰动下的局部可行燃油响应",
        [Line("燃油变化", beta["beta_factor"].tolist(), beta["fuel_delta_vs_nominal_kg"].tolist(), PURPLE, 2.5, None)],
        "β 因子",
        "相对标称燃油变化 / kg",
        "±20% 扰动下燃油波动不超过 14.116 kg，仅作局部敏感性描述",
        ref_y=(0, "标称"),
    )
    vals = [
        math.log10(float(res["terminal_height_error_m"]) / 1e-3),
        math.log10(float(res["terminal_speed_error_mps"]) / 1e-3),
        math.log10(float(res["fuel_identity_residual_kg"]) / 5e-2),
        -6.0 if float(res["max_scaled_constraint_violation"]) == 0 else math.log10(float(res["max_scaled_constraint_violation"])),
    ]
    horizontal_bar(
        FIG_DIR / "fig_v2_q4_validation_card.pdf",
        "问题四：有风局部优化连续验证",
        ["高度", "速度", "燃油", "约束"],
        vals,
        [GREEN, GREEN, GREEN, GREEN],
        "log10(残差/阈值)",
        "终端高度、速度、燃油恒等式和路径约束均通过验证",
        0,
    )


def main() -> None:
    configure()
    fig_q1()
    fig_q2()
    fig_q3()
    fig_q4()
    expected = [
        "fig_v2_q1_closure_mechanism.pdf",
        "fig_v2_q1_height_time.pdf",
        "fig_v2_q1_climb_rate.pdf",
        "fig_v2_q1_metric_comparison.pdf",
        "fig_v2_q2_density_correction.pdf",
        "fig_v2_q2_sound_speed_correction.pdf",
        "fig_v2_q2_fuel_accumulation.pdf",
        "fig_v2_q2_temperature_sensitivity.pdf",
        "fig_v2_q3_feasibility_bridge.pdf",
        "fig_v2_q3_state_corridor_height.pdf",
        "fig_v2_q3_state_corridor_mass.pdf",
        "fig_v2_q3_control_schedule.pdf",
        "fig_v2_q3_grid_stability.pdf",
        "fig_v2_q3_validation_dashboard.pdf",
        "fig_v2_q4_strategy_savings.pdf",
        "fig_v2_q4_height_profile_compare.pdf",
        "fig_v2_q4_control_profile.pdf",
        "fig_v2_q4_fixed_fuel_range.pdf",
        "fig_v2_q4_beta_sensitivity.pdf",
        "fig_v2_q4_validation_card.pdf",
    ]
    missing = [name for name in expected if not (FIG_DIR / name).exists()]
    if missing:
        raise RuntimeError(f"missing figures: {missing}")


if __name__ == "__main__":
    main()
