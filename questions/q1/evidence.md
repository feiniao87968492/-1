# q1 证据说明

本文件解释本小问关键主张的证据。机器可读索引以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q1-C01 | 在确认的 q1 模型下，两策略总燃油均为 `10450 kg`，总油耗无区分度 | `artifacts/q1/data/strategy_comparison.csv` | 终止质量固定为 `62000 kg`，初始质量 `72450 kg` | 这是题设终止条件导致，不是优化结论 | supported |
| Q1-C02 | 等速策略最终高度约 `10637.065 m`，用时约 `761.917 s`，航程约 `200668.442 m` | `artifacts/q1/data/constant_speed_profile.csv` 与 `strategy_comparison.csv` | `validation_summary.csv` 中初始条件、质量单调、升力和能量残差均通过 | 依赖小角度准稳态与 `CL=CL_ref` 闭合条件 | supported |
| Q1-C03 | 等马赫策略最终高度约 `10437.818 m`，用时约 `811.032 s`，航程约 `211331.296 m` | `artifacts/q1/data/constant_mach_profile.csv` 与 `strategy_comparison.csv` | `validation_summary.csv` 中初始条件、质量单调、升力和能量残差均通过 | 依赖标准声速模型和同一闭合条件 | supported |
| Q1-C04 | 本模型与确认参数下，等速策略平均爬升率高于等马赫策略 | `strategy_comparison.csv` | 平均爬升率按端点高度差除以总时间计算，分别为 `1.492374 m/s` 与 `1.156327 m/s` | 与题面“等马赫更大”的表述不一致；原因是声速随高度降低改变升力平衡分母 | supported |

## 验证摘要

`questions/q1/artifacts/tables/validation_summary.csv` 显示：

- 初始条件检查通过；
- 质量单调下降检查通过；
- 升力平衡残差最大值为 `0`；
- 能量方程残差最大量级约 `1e-16`；
- 步长敏感性检查通过，检查对象为报告指标 `final_time_s`、`final_distance_m` 和 `mean_climb_rate_mps`；
- 有风相对无风增加地面航程；
- 灵敏度表按 `configs/default.yaml` 中 `validation.sensitivity_relative_changes` 生成 `beta` 的 `-20%`、`-10%`、`+10%`、`+20%` 四个扰动场景；
- 极端高度和速度下大气与气动量保持正值。
