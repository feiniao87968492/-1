# q3 review5 对照审计

来源：`questions/q3/review5.md`

## 结论

review5 合理。当前版本仍然只是 Gate 2 dry-run/readiness，不是完整 collocation 可行性 Gate，也不是无风最优结果。本轮只补齐 dry-run 证据链缺口：投影差异审计、C1 大气数值诊断、`h_max` warm-start 表的准确命名，以及当前离散格式口径冻结。

## 逐项处理

| 编号 | review5 意见 | 状态 | 本轮处理 |
|---|---|---|---|
| R1 | dry-run 缺口距离 Gate 阈值仍很远，不能写成已通过 | kept | 文档继续保留 `dry_run_not_optimized`，不改变 q3 为 done，不生成正式最优结论。 |
| R2 | Gate 1 到 dry-run 的约 3.983 kg 差异需要拆分来源 | fixed | 新增 `questions/q3/artifacts/tables/gate1_to_collocation_projection_audit.csv`。A 原 Gate 1 `mf=61989.785554 kg`；B 插值到 Gate2 网格并按原分层 ISA 重推 `mf=61985.803328 kg`，差异 `3.982226 kg`；C 改为 C1 大气后 `mf=61985.803328 kg`，本投影口径下新增差异为 `0 kg`。 |
| R3 | C1 大气需要把端点连续性、静力残差、正值性写入结果表 | fixed | 新增 `questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv`，记录静力残差、温度导数跳变、最小温度/压力/密度、`dp/dh<0` 以及相对分层 ISA 的最大偏差。 |
| R4 | `h_max` sensitivity 只是 warm-start 诊断，不能叫 optimized sensitivity | fixed | 新增准确命名 `warm_start_hmax_diagnostic.csv`，保留旧 `no_wind_hmax_sensitivity.csv` 作为兼容输出；表内状态为 `warm_start_only_not_optimized`。 |
| R5 | 需要冻结当前 collocation 离散格式 | fixed | 在 `configs/default.yaml` 写入 `collocation_transcription: trapezoidal`。当前 dry-run 使用航程域梯形缺陷；Hermite-Simpson 留作正式 Gate 2 NLP 或后续加密版本。 |
| R6 | dry-run 阶段不需要伪造 KKT 诊断 | kept | 未新增 KKT 乘子或 Hamiltonian 最优性残差；KKT 诊断仍等待正式 NLP 乘子。 |
| R7 | 下一阶段应实现非 dry-run Gate 2 NLP | deferred | 记录为下一步任务；本轮未把未优化投影包装成 NLP 解。 |

## 本轮新增可复核产物

- `questions/q3/artifacts/tables/gate1_to_collocation_projection_audit.csv`
- `questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv`
- `questions/q3/artifacts/tables/warm_start_hmax_diagnostic.csv`

## 数值边界

- dry-run 终端质量缺口仍为 `14.196672 kg`，远大于 Gate 阈值 `0.05 kg`。
- dry-run 尺度化配点缺陷仍为约 `6.20e-05`，远大于 Gate 阈值 `1e-6`。
- C1 大气静力残差最大值约 `2.22e-16`；相对分层 ISA 最大偏差为温度 `0.08125 K`、压力 `0.044253 Pa`、密度 `1.36e-4 kg/m^3`。

因此，review5 后的结论是：Gate 2 dry-run 证据更完整，但完整 Gate 2 NLP 仍未实现，q3 不能标记为完成。
