# q3 review8 对照审计

来源：`questions/q3/review8.md`

## 结论

已按 review8 启动非 dry-run 的 Gate 2 无风可行性 NLP，但本次 `N=31` 结果仍不能判定 Gate 2 通过：第一阶段质量松弛和梯形配点缺陷已接近数值零，独立 ODE 重积分误差尚未满足正式门槛。

## 处理项

| Review 意见 | 处理 | 证据 | 状态 |
|---|---|---|---|
| 下一步应进入非 dry-run Gate 2 无风可行性 NLP，而不是继续增加 readiness 审计 | `solve_feasibility_collocation_no_wind.py` 新增非 dry-run 分支，节点状态/控制进入 SLSQP，第一阶段只最小化终端质量松弛 `s` | `questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv` | implemented |
| 第一阶段目标只应为 `min s` | 非 dry-run summary 标记 `lexicographic_stage=stage1_minimize_terminal_mass_slack`，目标函数只取松弛变量 | `tests/test_q3_gate2_readiness.py` | implemented |
| 需要独立 ODE 重积分诊断 | 正式 Gate 表输出 `reintegration_state_error_inf`、终端质量/高度/速度重积分误差，并将其纳入 Gate 状态判定 | `questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv` | implemented |
| 不能把配点缺陷小直接写成严格可行 | `N=31` 虽有 `s≈0` 和配点缺陷 `1.42e-14`，但因重积分速度误差 `0.0302 m/s`，review9 后状态修正为 `discrete_feasible_reintegration_failed` | `questions/q3/results.md` | resolved |
| 高度上界敏感性必须重新优化并输出 `optimized_hmax_sensitivity.csv` | 非 dry-run 分支对 `{10950,11500,12000,12500} m` 逐项重新运行 stage1 NLP，输出优化后敏感性表 | `questions/q3/artifacts/tables/optimized_hmax_sensitivity.csv` | implemented |

## `N=31` 关键数值

| 指标 | 数值 |
|---|---:|
| `solver_status` | `discrete_feasible_reintegration_failed` |
| `terminal_mass_slack_kg` | `2.484741e-12` |
| `terminal_mass_shortfall_kg` | `0.0` |
| `scaled_collocation_defect_inf` | `1.422772e-14` |
| `max_scaled_constraint_violation` | `0.0` |
| `reintegration_terminal_mass_error_kg` | `0.703760` |
| `reintegration_terminal_height_error_m` | `0.000994` |
| `reintegration_terminal_speed_error_mps` | `0.030218` |

## 边界

本轮证明非 dry-run Gate 2 求解链路已可运行，并且代数配点问题可把质量松弛压到零；但连续 ODE 重积分仍未通过，因此不能写成严格无风可行轨迹，更不能进入最终无风最省油轨迹或有风 continuation。
