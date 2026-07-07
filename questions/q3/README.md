# q3 — 小问 3

- 状态：`in_implementation`
- 负责人：Codex
- 依赖小问：q1 等速参考路径、q2 共同可行航程
- 正式入口：`python questions/q3/scripts/pipeline.py --dry-run`
- 预检查入口：`python questions/q3/scripts/precheck.py --config configs/default.yaml`
- 可行性 Gate：`python questions/q3/scripts/solve_feasibility_no_wind.py --config configs/default.yaml --nodes 21`
- collocation Gate dry-run：`python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 21 --dry-run`
- collocation Gate 非 dry-run：`python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 31`

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

## 任务目标

建立第三问最优控制模型的题意审计、优化问题定义、必要条件推导和直接法数值求解方案；本轮不生成正式最优轨迹和最优油耗数值。

## 输入

- 数据：`question.md`
- 上游结果：`artifacts/q1/data/constant_speed_profile.csv`、`artifacts/q2/data/q2_fuel_summary.csv`
- 参数 / 配置：`configs/default.yaml`

## 输出

- 核心数值或决策：固定比较航程 `Xf=189781.310 m`；终端高度 `h(tf)=10577.124 m`；终端速度 `V(tf)=240 m/s`
- 结果表：`questions/q3/artifacts/tables/baseline_feasibility.csv`，仅用于求解器前固定路径可行性预检查；`questions/q3/artifacts/tables/no_wind_feasibility_gate.csv`，用于无风可行性 Gate；`questions/q3/artifacts/tables/no_wind_collocation_gate.csv`，用于 Gate 2 dry-run/readiness 诊断
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
- [ ] 正式求解脚本完成
- [ ] 数值最优结果完成
- [ ] 图表和数据成对保存
- [ ] 支持性证据链完成
