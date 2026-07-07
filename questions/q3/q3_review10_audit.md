# q3 review10 对照审计

来源：`questions/q3/review10.md`

## 总体判断

review10 的判断合理。当前 Gate 2 结论应表述为：离散梯形 collocation 可行，但连续 ODE 重积分尚未通过；不能进入最终无风燃油最优求解。

## 逐条处理

| review10 意见 | 处理状态 | 处理说明 |
|---|---|---|
| `N=31,h_max=12000 m` 的失败点主要是重积分终端速度误差，不应继续放宽质量约束 | 已采纳 | 保持 `solver_status=discrete_feasible_reintegration_failed`，不放宽 `1e-3 m/s` 速度门槛 |
| 优先运行 `N=31->61->121` 网格收敛，并保存 `e_V,e_m` 和误差比 | 已完成 | 新增 `no_wind_collocation_mesh_convergence.csv`，保存质量误差、速度误差、相邻误差比、控制步长和总变差 |
| 若误差不下降，应检查模型一致性、ODE 容差、控制振荡和节点速度误差 | 部分完成 | 当前 `31/61/121` 误差比接近 4，暂未触发“误差不下降”；表中已新增控制步长、总变差、节点速度/质量重积分误差。ODE 容差敏感性留作后续 Gate 2 修正 |
| Stage 1B 可加入但不能替代网格收敛 | 已采纳 | `approach.md` 将 Stage 1B 写为后续连续一致性修正，且保留网格收敛为进入最终优化前门槛 |
| `approach.md` 中第二阶段 `s<=s_min+epsilon_s` 与 `s=0` 表述冲突 | 已修正 | 改为条件策略：若 `s_min<=epsilon_zero` 则固定 `s=0`，否则才允许 `s<=s_min+epsilon_s` |
| `manifest.yaml` 的 `collocation_feasibility` 不应继续为 `planned` | 已修正 | 改为 `partial`，并新增 mesh convergence 输出路径 |
| Q3-C06 不应继续为 `planned` | 已修正 | `docs/evidence_chain.csv` 与 `questions/q3/evidence.md` 中 Q3-C06 改为 `supported`，并注明连续重积分/网格收敛未通过 |
| 仍不能进入最终无风燃油优化 | 已采纳 | `results.md`、`approach.md` 和证据链均保留该限制 |

## 新增正式数值

`questions/q3/artifacts/tables/no_wind_collocation_mesh_convergence.csv` 当前记录：

| N | 质量误差 kg | 速度误差 m/s | 质量误差比 | 速度误差比 | gate_status |
|---:|---:|---:|---:|---:|---|
| 31 | 0.703760 | 0.030218 |  |  | discrete_feasible_reintegration_failed |
| 61 | 0.174045 | 0.007656 | 4.044 | 3.947 | discrete_feasible_reintegration_failed |
| 121 | 0.045053 | 0.001897 | 3.863 | 4.035 | discrete_feasible_reintegration_failed |

结论：误差基本按梯形法二阶趋势下降，但 `N=121` 的终端速度重积分误差仍高于 `1e-3 m/s`，所以 Gate 2 仍未通过。

## 复现命令

```bash
python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 31 --mesh-study-nodes 31,61,121 --skip-hmax-sensitivity
python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 31
python -m pytest tests/test_q3_gate2_readiness.py -q
```
