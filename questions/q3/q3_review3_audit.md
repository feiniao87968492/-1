# q3 review3 对照审计

来源：`questions/q3/review3.md`

## 结论

review3 合理。当前低维无风可行性 Gate 已接近可行，但仍不是严格可行解，也不是正式最优解。本轮不继续扩写 PMP，也不开始有风最优求解；优先修复 Gate 1 的证据解释问题，并把下一阶段明确为完整航程域 collocation 可行性 NLP。

## 逐项处理

| 编号 | review3 意见 | 状态 | 本轮处理 |
|---|---|---|---|
| R1 | Gate 1 是实质进展，但不能称为可行解 | fixed | `results.md` 保留 `needs_relaxation`，说明 `s*=10.214 kg` 仍未达到严格可行 |
| R2 | “最大约束违反为 0”字段有歧义 | fixed | 表字段改为 `max_nonrelaxed_constraint_violation`，质量缺口单独写为 `terminal_mass_shortfall_kg` |
| R3 | `6.94e-18` 不是完整 collocation 缺陷 | fixed | 表字段改为 `integration_consistency_residual`；正式配点缺陷保留为后续 `collocation_defect_max` |
| R4 | 下一步应进入完整 collocation 可行性 NLP | planned | 文档和 devlog 将下一阶段锁定为 Gate 2A/2B/2C，不启动有风最优解 |
| R5 | 可行性达到 `s=0` 后目标会退化 | fixed | `approach.md` 明确 Gate 2 只找可行轨迹，之后才进入无风燃油最优 |
| R6 | Gate 1 需报告飞行包线和活跃约束 | fixed | `no_wind_feasibility_gate.csv` 新增高度、速度、推力、航迹角、马赫、升力系数范围及最小余量 |
| R7 | 飞行包线透明度不足 | fixed | `results.md` 直接列出配置边界和 Gate 1 轨迹范围 |
| R8 | 怠速推力问题可从 Gate 1 数据初判 | fixed | `results.md` 报告 Gate 1 最小推力 `25647.548 N`，未贴近 `T=0` |
| R9 | 固定路径松弛数值不统一 | fixed | Gate 表优先引用 `baseline_feasibility.csv`，统一为 `836.526 kg` |
| R10 | 产物 ID 重复 | fixed | 产物规划改为 `q3-T00/T01/T02/T03` |
| R11 | `brief.md` “只冻结设计”表述过时 | fixed | `brief.md` 改为不输出正式最优，但输出预检查和 Gate 1 数值 |

## Gate 1 关键诊断

| 指标 | 数值 |
|---|---:|
| 固定路径质量缺口 | 836.526 kg |
| Gate 1 质量缺口 | 10.214 kg |
| Gate 1 终端质量 | 61989.786 kg |
| Gate 1 总时间 | 802.883 s |
| 高度范围 | 9500.000 到 12000.000 m |
| 空速范围 | 234.373 到 240.000 m/s |
| 推力范围 | 25647.548 到 72018.170 N |
| 航迹角范围 | -0.026406 到 0.037501 rad |
| 最大马赫数 | 0.808724 |
| 升力系数范围 | 0.489343 到 0.667625 |

高度上界几乎激活，说明后续完整 collocation 和敏感性分析应优先检查 `h_max` 对可行性的影响。当前最小推力远大于 0，因此 Gate 1 轨迹本身没有依赖零推力滑翔。
