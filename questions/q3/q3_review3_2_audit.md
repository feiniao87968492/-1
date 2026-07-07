# q3 review3 (2) 对照审计

来源：`questions/q3/review3 (2).md`

## 结论

review3(2) 合理。上一轮已经完成 Gate 1 证据解释修订；本轮不继续生成低维 Gate 结果，也不启动有风最优求解，而是补齐进入完整航程域 collocation Gate 前必须冻结的技术口径。

## 逐项处理

| 编号 | review3(2) 意见 | 状态 | 本轮处理 |
|---|---|---|---|
| R1 | Gate 1 解释正确，但高度上界显著影响结论 | fixed | `results.md` 和 `approach.md` 明确当前结论依赖 `h_max=12000 m`；新增 `h_max={10950,11500,12000,12500} m` 敏感性要求 |
| R2 | 12 km 轨迹与 11 km 大气层导数处理冲突 | fixed | `configs/default.yaml` 和 `approach.md` 规定 Gate 2 默认采用 `10950-11050 m` 的 `C1` 平滑层间过渡 |
| R3 | 航程域配点乘子不能直接用于时间域 PMP | fixed | `derivation.md` 新增航程域 Hamiltonian `H_x` 和 KKT 诊断口径 |
| R4 | 可行性目标和平滑正则必须分层优化 | fixed | `approach.md` 与配置写入词典序策略：先 `min s`，再在固定松弛容差内平滑控制 |
| R5 | 必须定义 `s*≈0` 的数值标准 | fixed | `configs/default.yaml` 和 `results.md` 写入 Gate 通过门槛：`s<=0.05 kg`、尺度化缺陷 `<=1e-6` 等 |
| R6 | 飞行包线仍需说明来源 | fixed | `results.md` 明确当前边界是仿真边界，贴边结论只在该设定下成立；`risk_register.md` 已记录高度上界驱动风险 |
| R7 | 怠速推力对 Gate 1 暂不构成影响 | fixed | `results.md` 保留最小推力 `25647.548 N`，但正式燃油最优仍需做 `T_idle` 敏感性 |
| R8 | 状态保持 `in_design` 合理 | fixed | `manifest.yaml` 不改为 done；完整 collocation Gate 未完成 |

## 下一阶段门槛

Gate 2 不能只做“增加节点”。完整可行性判断必须同步包含：

1. 航程域完整 collocation NLP；
2. `h_max` 敏感性；
3. 11 km 大气层 `C1` 平滑过渡或对流层内替代方案；
4. 航程域 KKT 诊断，而不是直接套用时间域 PMP；
5. 词典序目标，防止控制平滑牺牲可行性。
