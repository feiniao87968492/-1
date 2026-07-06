# q2 证据说明

本文件解释本小问关键主张的证据。机器可读索引仍以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q2-C01 | 固定 q1 等速参考航程下，标准 ISA 总油耗约 `11004.536 kg` | `artifacts/q2/data/q2_fuel_summary.csv` | `questions/q2/artifacts/tables/validation_summary.csv` 固定航程、正性、路径积分和步长敏感性检查通过 | 沿用 q1 等速固定 `CL_ref` 操作规律，不是最优路径 | supported |
| Q2-C02 | 静力平衡 `+10 K` 常温偏差使固定航程总油耗增加约 `34.810 kg`，约 `0.316%` | `artifacts/q2/data/q2_fuel_summary.csv`; `artifacts/q2/data/q2_temperature_sensitivity.csv`; `questions/q2/artifacts/figure_data/temperature_sensitivity.csv` | 静力平衡残差、`DeltaT=0` 收敛、正负温差响应和路径/时间积分一致性检查通过 | 常温偏差示例；未加入等马赫、波阻或马赫相关发动机效率 | supported |
| Q2-C03 | 在当前固定真空速、固定 `CL_ref` 模型中，`|DeltaT|<=10 K` 的总油耗变化小于 `0.4%` | `artifacts/q2/data/q2_temperature_sensitivity.csv` | 多温差场景全部通过 q2 验证表 | 仅对当前操作规律、常温偏差和题设参数成立 | supported |
