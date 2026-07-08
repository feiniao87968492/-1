# q3 review9 对照审计

来源：`questions/q3/review9.md`

## 总体判断

review9 合理。`N=31` 非 dry-run Gate 2 一阶段 NLP 已经证明离散配点层面可以把质量松弛、配点缺陷和节点约束违反压到数值零附近，但这不能等价为连续 ODE 轨迹可行。当前失败点是重积分速度误差超出 `1e-3 m/s` 门槛，而不是质量约束还需要放松。

## 处理结果

| review9 要点 | 处理 | 产物 |
|---|---|---|
| `needs_relaxation` 对当前结果不准确 | 已将正式 Gate 状态改为 `discrete_feasible_reintegration_failed` | `no_wind_collocation_formal_gate.csv` |
| 必须明确重积分控制重构方法 | 新增 `control_reconstruction=piecewise_linear_node_controls` | `solve_feasibility_collocation_no_wind.py` |
| 重积分终端误差需报告符号和实际终端质量 | 新增重积分终端质量、有符号质量误差、质量短缺、高度/速度有符号误差 | `no_wind_collocation_formal_gate.csv` |
| 每个 `h_max` 方案需报告连续诊断 | `optimized_hmax_sensitivity.csv` 新增重积分质量短缺、速度误差、活跃高度上界比例和 `gate_status` | `optimized_hmax_sensitivity.csv` |
| README 完成条件过粗 | 拆分为 Stage 1 脚本、重积分/网格收敛、正式燃油优化脚本和正式结果 | `questions/q3/README.md` |
| `brief.md` 中完整 collocation 未实现的表述过时 | 改为 Stage 1 已实现但连续重积分未通过 | `questions/q3/brief.md` |
| `N=61/121` 网格收敛需要执行 | 已记录为下一阶段门槛；本次未把 Gate 2 标记为通过 | `approach.md`; `results.md`; `risk_register.md` |

## 当前正式结果

`N=31,h_max=12000 m`：

| 指标 | 数值 |
|---|---:|
| `terminal_mass_slack_kg` | `2.48e-12` |
| `scaled_collocation_defect_inf` | `1.42e-14` |
| `max_scaled_constraint_violation` | `0` |
| `reintegration_terminal_mass_kg` | `62000.703760` |
| `reintegration_terminal_mass_signed_error_kg` | `+0.703760` |
| `reintegration_terminal_mass_shortfall_kg` | `0` |
| `reintegration_terminal_height_signed_error_m` | `-0.000994` |
| `reintegration_terminal_speed_signed_error_mps` | `+0.030218` |
| `solver_status` | `discrete_feasible_reintegration_failed` |

## 未完成项

- 尚未运行并归档 `N=61/121` 网格收敛比 `e31/e61`、`e61/e121`。
- 尚未实现 Stage 1B 控制平滑选择。
- 尚未进入最终无风燃油优化，也没有有风 continuation 结果。
