# q3 — 小问 3

- 状态：`in_implementation`
- 负责人：Codex
- 依赖小问：q1 等速参考路径、q2 共同可行航程
- 正式入口：`python questions/q3/scripts/pipeline.py --dry-run`
- 预检查入口：`python questions/q3/scripts/precheck.py --config configs/default.yaml`
- 可行性 Gate：`python questions/q3/scripts/solve_feasibility_no_wind.py --config configs/default.yaml --nodes 21`
- collocation Gate dry-run：`python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 21 --dry-run`
- collocation Gate 非 dry-run：`python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 31`
- collocation Gate 正式通过诊断：`python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 241 --mesh-study-nodes 31,61,121,241 --skip-hmax-sensitivity --ode-rtols 1e-8,1e-10,1e-12`

review5 后新增 dry-run 诊断表：

- `questions/q3/artifacts/tables/gate1_to_collocation_projection_audit.csv`
- `questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv`
- `questions/q3/artifacts/tables/warm_start_hmax_diagnostic.csv`

review6 后新增代码级耦合诊断表：

- `questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv`

review7 后补充 Gate 2 readiness 约束：

- `atmosphere_coupling_diagnostics.csv` 新增 required-thrust 口径，验证 C1 大气差异可经 `D -> T_required -> dm/dx` 传导到燃油率；
- `atmosphere_smoothing_diagnostics.csv` 新增无量纲有限差分静力残差的步长敏感性 `{0.1,0.5,1,2,5} m`；
- 正式非 dry-run Gate 2 必须报告独立 ODE 重积分误差，不能只依赖梯形配点代数残差。

review8 后新增非 dry-run Gate 2 产物：

- `questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv`
- `questions/q3/artifacts/tables/no_wind_collocation_formal_trajectory.csv`
- `questions/q3/artifacts/tables/optimized_hmax_sensitivity.csv`

review9 后修正 Gate 2 formal 诊断口径：

- 正式 Gate 表新增 `control_reconstruction=piecewise_linear_node_controls` 和重积分终端有符号误差；
- `N=31` 当前状态改为 `discrete_feasible_reintegration_failed`，表示离散 NLP 可行但连续 ODE 重积分未过门槛；
- `optimized_hmax_sensitivity.csv` 每行新增重积分质量短缺、速度误差、活跃高度上界比例和 `gate_status`。

review10 后新增网格收敛诊断：

- 新增 `questions/q3/artifacts/tables/no_wind_collocation_mesh_convergence.csv`；
- `N=31->61->121` 的重积分速度误差比约为 `3.95` 和 `4.04`，符合梯形法二阶下降趋势；
- `N=121` 速度误差仍为 `0.001897 m/s`，高于 `1e-3 m/s` 门槛，因此 review10 阶段 Gate 2 仍未通过；该历史结论已由 review11 的 `N=241` 结果更新。

review11 后新增 `N=241`、ODE 容差和连续路径审计：

- `questions/q3/artifacts/tables/no_wind_collocation_mesh_convergence.csv` 扩展到 `N=241`；
- 新增 `questions/q3/artifacts/tables/no_wind_collocation_reintegration_tolerance.csv`；
- 新增 `questions/q3/artifacts/tables/no_wind_collocation_continuous_audit.csv`；
- `N=241` 的重积分速度误差约 `4.806e-4 m/s`，连续约束违反为 `0`，Gate 2 可行性门槛已通过；这仍不是最终燃油最优解。

本轮最终无风燃油优化结果：

- 新增 `questions/q3/artifacts/tables/no_wind_final_optimal_results.csv`；
- 新增 `questions/q3/artifacts/tables/no_wind_final_optimal_validation.csv`；
- 新增 `questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv`；
- 新增 `questions/q3/artifacts/tables/no_wind_final_optimal_diagnostics.csv`；
- 新增 `questions/q3/artifacts/tables/no_wind_final_hmax_sensitivity.csv`；
- 新增 `questions/q3/artifacts/tables/no_wind_final_idle_thrust_sensitivity.csv`；
- `N=61 -> 121 -> 241` reduced-control shooting continuation 已通过 q3-T08 验收：燃油 `10342.814 kg`，终端质量 `62107.186 kg`，`tf/t_base=1.01887`，`validation_status=passed`。
- 该结果是当前无风最终燃油优化主结果；`h_max` 和怠速推力敏感性已有 `N=121` 局部重优化表，但 Q3 整体仍需补 `N=241` hmax/怠速加强、基础油耗扩展、PMP/Hamiltonian 诊断和有风 continuation，暂不标记为 `done`。

## 任务目标

建立第三问最优控制模型的题意审计、优化问题定义、必要条件推导、直接法数值求解方案，并给出通过验收的无风最终燃油优化结果。

## 输入

- 数据：`question.md`
- 上游结果：`artifacts/q1/data/constant_speed_profile.csv`、`artifacts/q2/data/q2_fuel_summary.csv`
- 参数 / 配置：`configs/default.yaml`

## 输出

- 核心数值或决策：固定比较航程 `Xf=189781.310 m`；终端高度 `h(tf)=10577.124 m`；终端速度 `V(tf)=240 m/s`
- 结果表：`questions/q3/artifacts/tables/baseline_feasibility.csv`，用于求解器前固定路径可行性预检查；`questions/q3/artifacts/tables/no_wind_feasibility_gate.csv`，用于无风可行性 Gate；`questions/q3/artifacts/tables/no_wind_collocation_gate.csv`，用于 Gate 2 dry-run/readiness 诊断；`questions/q3/artifacts/tables/no_wind_collocation_mesh_convergence.csv`，用于 Gate 2 重积分误差网格收敛诊断；`questions/q3/artifacts/tables/no_wind_collocation_reintegration_tolerance.csv` 和 `questions/q3/artifacts/tables/no_wind_collocation_continuous_audit.csv`，用于 `N=241` 的 ODE 容差与连续路径审计；`questions/q3/artifacts/tables/no_wind_final_optimal_results.csv` 和 `questions/q3/artifacts/tables/no_wind_final_optimal_validation.csv`，用于无风最终燃油优化结果和验收；`questions/q3/artifacts/tables/no_wind_final_hmax_sensitivity.csv`，用于最终燃油目标下的 `h_max` 局部重优化敏感性；`questions/q3/artifacts/tables/no_wind_final_idle_thrust_sensitivity.csv`，用于最终燃油目标下的怠速推力下界局部敏感性。
- 图：本轮不生成论文级图
- 生图数据：本轮不生成生图数据

## 完成条件

- [x] 题意和数学目标明确
- [x] 优化问题定义完成
- [x] 必要条件推导完成
- [x] 直接法求解方案完成
- [x] 验证计划完成
- [x] 固定路径有风/无风可行性预检查完成
- [x] 无风可行性 Gate 初版完成
- [x] Gate 2 dry-run 入口和 C1 平滑大气诊断完成
- [x] Gate 2 dry-run 投影差异、C1 大气和 warm-start hmax 诊断表完成
- [x] 正式 Gate 2 Stage 1 可行性求解脚本完成
- [x] Gate 2 连续重积分与网格收敛通过
- [x] 正式无风燃油优化脚本入口完成
- [x] 正式无风最优结果完成
- [ ] 图表和数据成对保存
- [x] 支持性证据链完成
