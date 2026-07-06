# q2 证据说明

本文件解释本小问关键主张的证据。机器可读索引仍以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q2-C01 | 固定 q1 等速参考航程下，标准 ISA 总油耗约 `11004.536 kg` | `artifacts/q2/data/q2_fuel_summary.csv` | `questions/q2/artifacts/tables/validation_summary.csv` 固定航程和正性检查通过 | 沿用 q1 等速固定 `CL_ref` 策略，不是最优路径 | supported |
| Q2-C02 | `+10 K` 完整温度修正使固定航程总油耗减少约 `129.665 kg`，约 `1.178%` | `artifacts/q2/data/q2_fuel_summary.csv`; `questions/q2/artifacts/figure_data/fuel_rate_path.csv` | 温度修正效应检查通过，油耗变化非零 | 常温偏差示例；压力剖面仍用 ISA 压力 | supported |
