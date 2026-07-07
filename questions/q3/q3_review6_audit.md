# q3 review6 对照审计

来源：`questions/q3/review6.md`

## 总体判断

review6 合理。它指出的关键问题不是继续扩写 dry-run 文档，而是把当前 dry-run 证据链中仍可能误读的两点做成可复现检查：C1 大气是否真正进入动力学调用链，以及静力残差是否只是在构造恒等式上自证。本轮已补代码级诊断和测试，但仍不把 q3 标记为完成。

## 处理记录

| 编号 | review6 意见 | 状态 | 本轮处理 |
|---|---|---|---|
| R1 | `m_f^B=m_f^C` 为 0 需要验证 C1 大气确实进入动力学 | fixed | 新增 `atmosphere_coupling_diagnostics.csv`，在 `h=11000 m,V=235 m/s,m=67000 kg,T=50000 N,gamma=0` 下分别调用分层 ISA 与 C1 大气，输出密度、阻力、`dV/dx` 和 `dm/dx` 差异。 |
| R2 | 静力残差 `2.22e-16` 可能来自构造恒等式 | fixed | `atmosphere_smoothing_diagnostics.csv` 新增基于生成压力函数中心差分的 `hydrostatic_residual_numerical_max/rms/max_height_m`。 |
| R3 | 第一版正式 NLP 应继续使用梯形配点，不急于切换 Hermite-Simpson | accepted | 维持 `collocation_transcription: trapezoidal`；本轮未更改离散格式。 |
| R4 | manifest 旧 `hmax_sensitivity` 入口易被误读 | fixed | outputs 中移除 `hmax_sensitivity`，保留 `legacy_warm_start_hmax_diagnostic` 作为旧表兼容入口，并预留 `optimized_hmax_sensitivity`；质量门也改为 `optimized_hmax_sensitivity`。 |
| R5 | 继续 review dry-run 的边际价值低，下一步应实现非 dry-run NLP | accepted | 文档继续标注 q3 为 `in_implementation`，下一步仍是非 dry-run Gate 2 NLP。 |

## 关键数值

| 诊断 | 数值 | 解释 |
|---|---:|---|
| C1 相对分层 ISA 密度差 | `-1.360695652e-4 kg/m^3` | C1 大气与分层 ISA 在动力学调用点可区分。 |
| C1 相对分层 ISA 阻力差 | `-2.843277 N` | 阻力和加速度链路确实受大气选择影响。 |
| C1 相对分层 ISA `dV/dx` 差 | `1.805829e-7 1/m` | C1 大气已经接入 `_rates` 的速度方程。 |
| C1 相对分层 ISA `dm/dx` 差 | `0.0 kg/m` | 当前固定推力 mass-rate 公式不含密度/阻力，因此 B 到 C 终端质量相同是模型结构结果，不是 C1 未接入。 |
| 构造式静力残差最大值 | `2.219177e-16` | 只说明内部公式一致。 |
| 有限差分静力残差最大值 | `1.194341e-08` | 更能说明生成的压力函数数值上满足静力平衡。 |
| 有限差分静力残差 RMS | `2.098546e-09` | 在审计网格上稳定。 |

## 新增或修改产物

- `questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv`
- `questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv`
- `questions/q3/manifest.yaml`
- `tests/test_q3_gate2_readiness.py`

## 结论边界

本轮只能支持：C1 大气已经进入动力学密度、阻力和 `dV/dx` 链路；当前固定推力 warm-start 投影中 `dm/dx` 不随密度变化，因此 C1 切换未改变终端质量。它仍不能支持任何正式无风最优油耗、`s*(h_max)` 或 Gate 2 通过结论。
