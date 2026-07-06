# q2 证据说明

本文件解释本小问关键主张的证据。机器可读索引仍以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q2-C01 | 固定 q1 等速几何路径并采用共同可行航程 `189781.310 m` 时，标准 ISA 总油耗约 `10427.256 kg` | `artifacts/q2/data/q2_fuel_summary.csv` | `questions/q2/artifacts/tables/validation_summary.csv` 初始状态、终点质量、固定航程、正性、路径积分和步长敏感性检查通过 | q1 等速路径不是最优路径；共同航程短于完整 q1 航程 | supported |
| Q2-C02 | 静力平衡 `+10 K` 常温偏差使共同可行航程总油耗增加约 `22.744 kg`，约 `0.218%` | `artifacts/q2/data/q2_fuel_summary.csv`; `artifacts/q2/data/q2_temperature_sensitivity.csv`; `questions/q2/artifacts/figure_data/temperature_sensitivity.csv` | 静力平衡残差、`DeltaT=0` 收敛、正负温差响应、终点质量约束和路径/时间积分一致性检查通过 | 常温偏差示例；未加入等马赫、波阻或马赫相关发动机效率 | supported |
| Q2-C03 | 在当前固定 q1 几何路径、固定真空速模型中，`|DeltaT|<=10 K` 的总油耗变化小于 `0.3%` | `artifacts/q2/data/q2_temperature_sensitivity.csv` | 多温差场景全部通过 q2 验证表 | 仅对当前路径、常温偏差和题设参数成立 | supported |
