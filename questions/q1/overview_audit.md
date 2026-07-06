# q1 与 `tasks/overview.md` 对比审计

## 审计结论

q1 已按 `tasks/task1.txt` 完成建模、推导、代码、数值实验、验证和证据链。总体采用 `tasks/overview.md` 的统一建模口径，但有两处需要明确记录的差异：

1. 主风场公式采用用户确认且 OCR 题面一致的 `W(h)=20+3e-5(h-10000)^2`，不采用 `overview.md` 早期建议的 `3e-6`。
2. `overview.md` 提醒“不应预设等马赫数爬升率一定更大”。数值结果表明，在当前模型和参数下，等速策略平均爬升率更高，因此最终结论没有迎合题面预设。

## 条目审计

| overview 要点 | 当前 q1 实现 | 证据 | 状态 |
|---|---|---|---|
| “水平飞行”解释为小角度准稳态巡航爬升 | 已采用 | `questions/q1/review.md`, `questions/q1/derivation.md` | matched |
| 状态变量为 `(x,h,V,m)`，物理控制量为 `(T,gamma)` | 已采用 | `questions/q1/approach.md` | matched |
| 不在巡航爬升中令 `T=D` | 已采用能量方程 `T=D+m dV/dt+mg dh/(Vdt)` | `questions/q1/derivation.md`, `questions/q1/scripts/simulate.py` | matched |
| 气动力模型采用小角度升力平衡与抛物线阻力极曲线 | 已采用 | `questions/q1/scripts/aircraft_model.py` | matched |
| 两策略需增加闭合条件 `CL=CL*` | 已采用 | `questions/q1/approach.md`, `questions/q1/scripts/strategy_constant_speed.py`, `strategy_constant_mach.py` | matched |
| 等真空速高度规律 `h=h0-Hrho ln(m/m0)` | 已采用 | `questions/q1/derivation.md`, `strategy_constant_speed.py` | matched |
| 等马赫数使用 `V=M0 a(h)` | 已采用 | `questions/q1/derivation.md`, `strategy_constant_mach.py` | matched |
| 不预设等马赫爬升率更大 | 已采用；结果显示等速平均爬升率更大 | `artifacts/q1/data/strategy_comparison.csv`, `questions/q1/results.md` | matched |
| 隐式质量微分方程 | 已采用 | `questions/q1/scripts/simulate.py` | matched |
| 固定终止质量下总油耗无区分度 | 已采用并登记证据链 | `docs/evidence_chain.csv`, `questions/q1/evidence.md` | matched |
| 风场公式需修正 | 已修正，但系数为用户确认 `3e-5`，不是 overview 建议 `3e-6` | `docs/decision_log.md`, `questions/q1/review.md` | intentionally different |
| `cT=2.8e-5` 作为工程合理性对照 | 已作为敏感性场景 | `questions/q1/artifacts/tables/sensitivity_summary.csv` | matched |

## 产物核验

| 要求 | 当前产物 | 状态 |
|---|---|---|
| `questions/q1/review.md` | 已完成 | pass |
| `questions/q1/derivation.md` | 已完成 | pass |
| 拆分脚本 | `atmosphere.py`, `aircraft_model.py`, `strategy_constant_speed.py`, `strategy_constant_mach.py`, `simulate.py`, `validate.py`, `visualize.py` | pass |
| 两策略完整时间序列 | `artifacts/q1/data/constant_speed_profile.csv`, `constant_mach_profile.csv` | pass |
| 汇总结果 | `artifacts/q1/data/strategy_comparison.csv` | pass |
| 五张图及同名生图数据/元数据 | `questions/q1/artifacts/figures/*.png`, `figure_data/*.csv`, `*.meta.json` | pass |
| 验证 | `questions/q1/artifacts/tables/validation_summary.csv` | pass |
| 文档更新 | `approach.md`, `experiments.md`, `evidence.md`, `results.md`, `manifest.yaml`, `devlog.md` | pass |
| 证据链和图表登记 | `docs/evidence_chain.csv`, `docs/figure_table_registry.csv` | pass |

## 剩余风险

- q1 仍是机理仿真模型，不是飞机工程认证模型。
- 未建模跨音速波阻、发动机推力包线和空管约束。
- `CL=CL*` 是为 q1 两种策略闭合而引入的假设，应在论文中明确说明。
