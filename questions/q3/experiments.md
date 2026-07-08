# q3 实验记录

## 实验矩阵

| 实验 ID | 日期 | 目标 | 数据版本 | 模型 / 配置 | 指标 | 结果 | 决策 |
|---|---|---|---|---|---|---|---|
| q3-E00 | 2026-07-06 | 题意审计和优化问题冻结 | `question.md`; q1/q2 产物 | 文档设计 | 是否存在退化目标、边界条件是否公平、求解路线是否明确 | 完成审计，不生成最优数值 | 进入后续脚本实现前的设计基线 |
| q3-E01 | 2026-07-07 | 求解器前固定路径可行性预检查 | `artifacts/q1/data/constant_speed_profile.csv`; `configs/default.yaml` | q1 等速路径，配置风场/无风分别积分 | 终端质量、距离误差、燃油积分误差、基线可行性 | 配置风场可行：`m_f=62022.744 kg`；无风不可行：`m_f=61163.474 kg` | q2 有风基线不能直接作为无风可行初值；q3 继续保持 `in_design` |
| q3-E02 | 2026-07-07 | 无风可行性 Gate | `artifacts/q1/data/constant_speed_profile.csv`; `configs/default.yaml` | 航程域参数化可行性搜索，目标为最小终端质量缺口 | `s*`、终端状态误差、非松弛约束违反、积分一致性残差、飞行包线余量 | `s*=10.214 kg`，固定路径缺口为 `836.526 kg`；状态为 `needs_relaxation` | 不能进入正式无风最优求解；需扩展为完整 collocation 可行性 NLP |
| q3-E03 | 2026-07-07 | Gate 2 dry-run/readiness | `questions/q3/artifacts/tables/no_wind_feasibility_trajectory.csv`; `configs/default.yaml` | C1 静力一致大气；Gate 1 warm start 投影；不执行优化 | 终端质量缺口、尺度化配点缺陷、无量纲约束违反、中点高度越界、`h_max` warm-start 敏感性 | dry-run 终端质量缺口约 `14.197 kg`，尺度化配点缺陷约 `6.20e-05`，状态为 `dry_run_not_optimized` | 只能证明投影和诊断链可运行；完整 Gate 2 NLP 仍未通过 |
| q3-E04 | 2026-07-07 | review5 dry-run 证据补强 | `questions/q3/artifacts/tables/no_wind_feasibility_trajectory.csv`; `configs/default.yaml` | 航程域梯形 dry-run；C1 大气诊断；Gate 1 到 Gate 2 投影审计 | 投影质量差异、静力残差、C1 正值性、`h_max` warm-start 越界 | Gate1 原轨迹到 Gate2 网格重推质量差异 `3.982 kg`；C1 大气静力残差约 `2.22e-16`；`h_max=10950 m` warm-start 越界约 `1050 m` | dry-run 证据链更完整，但不替代正式 Gate 2 NLP |
| q3-E05 | 2026-07-07 | review6 C1 耦合与独立静力残差审计 | `questions/q3/artifacts/tables/no_wind_feasibility_trajectory.csv`; `configs/default.yaml` | 航程域梯形 dry-run；固定状态点 C1/分层 ISA 对比；生成压力函数中心差分 | 密度差、阻力差、`dV/dx` 差、`dm/dx` 差、有限差分静力残差 | C1 与分层 ISA 在 11000 m 的密度差 `-1.36e-4 kg/m^3`、阻力差 `-2.843 N`、`dV/dx` 差 `1.806e-7 1/m`；固定推力下 `dm/dx` 差为 `0`；有限差分静力残差最大值 `1.19e-08` | C1 已接入动力学密度/阻力链路；B 到 C 质量差为 0 是当前 fixed-thrust mass-rate 结构结果，不是最终优化结论 |
| q3-E06 | 2026-07-07 | review7 required-thrust 燃油耦合与静力残差步长敏感性 | `questions/q3/artifacts/tables/no_wind_feasibility_trajectory.csv`; `configs/default.yaml` | 固定状态点所需推力反算；C1 大气有限差分静力残差步长扫描 | `T_req` 差、required-thrust `dm/dx` 差、无量纲静力残差步长敏感性、正式 Gate 2 诊断字段配置 | `T_req` 差 `-2.843277 N`，required-thrust `dm/dx` 差 `3.387735e-06 kg/m`；静力残差最大值从 `4.750640e-10` 到 `1.194352e-06` | 固定状态下燃油耦合链路已验证；正式非 dry-run Gate 2 仍需 NLP、重积分诊断和网格收敛 |
| q3-E07 | 2026-07-07 | review8 非 dry-run Gate 2 无风可行性 NLP | `questions/q3/artifacts/tables/no_wind_feasibility_trajectory.csv`; `configs/default.yaml` | 航程域梯形配点；一阶段目标 `min s`；SLSQP；独立 ODE 重积分 | 质量松弛、配点缺陷、状态/控制约束违反、重积分终端误差、优化后 `h_max` 敏感性 | `N=31` 下 `s=2.48e-12 kg`、配点缺陷 `1.42e-14`、约束违反 `0`；但重积分速度误差 `0.0302 m/s` | 非 dry-run 求解链路可运行，但未通过连续 ODE 重积分门槛；不能进入最终最优燃油求解 |
| q3-E08 | 2026-07-07 | review9 Gate 2 重积分诊断收口 | `questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv`; `questions/q3/artifacts/tables/optimized_hmax_sensitivity.csv` | 分段线性节点控制重构；重积分有符号终端误差；每个 `h_max` 方案独立 gate 状态 | `control_reconstruction`、重积分终端质量/符号误差/质量短缺、速度误差、`active_hmax_fraction`、`gate_status` | `N=31` 状态改为 `discrete_feasible_reintegration_failed`；重积分终端质量 `62000.704 kg`、质量短缺 `0 kg`、速度误差 `0.0302 m/s`；四个 `h_max` 方案均未过连续重积分速度门槛 | Gate 2 尚未通过；下一步运行 `N=61/121` 网格收敛，必要时加入 Stage 1B 控制平滑或更高阶转录 |
| q3-E09 | 2026-07-07 | review10 Gate 2 网格收敛诊断 | `questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv`; `configs/default.yaml` | 基准 `h_max=12000 m`；`N=31/61/121`；一阶段目标 `min s`；独立 ODE 重积分；分段线性节点控制 | `e_m`、`e_V`、误差比、控制步长、控制总变差、节点速度重积分误差 | 速度误差 `0.030218 -> 0.007656 -> 0.001897 m/s`，速度误差比 `3.947`、`4.035`；质量误差比 `4.044`、`3.863`；`N=121` 仍高于 `1e-3 m/s` 门槛 | review10 阶段 Gate 2 尚未通过；该历史限制已由 q3-E10 的 `N=241` 结果解除 |
| q3-E10 | 2026-07-07 | review11 `N=241`、ODE 容差和沿程连续审计 | `questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv`; `configs/default.yaml` | 基准 `h_max=12000 m`；`N=241`；一阶段目标 `min s`；`rtol={1e-8,1e-10,1e-12}`；沿程 dense 重积分审计 | `e_m`、`e_V`、ODE 容差相邻差异、沿程状态误差、连续约束违反 | `N=241` 速度误差 `0.000481 m/s`、质量误差 `0.010663 kg`；相对 `N=121` 速度误差比 `3.948`；ODE 容差下终端速度相邻差异最大约 `3.22e-6 m/s`；连续约束违反为 `0` | Gate 2 连续可行性门槛通过；下一步可进入最终无风燃油最优求解实现，但当前结果仍不是燃油最优 |
| q3-E11 | 2026-07-08 | review13 可行性收口文档审查 | `questions/q3/review13.md`; `questions/q3/q3_review12_audit.md` | 文档一致性审计 | 是否还存在“仅计划”“求解器前”和误用 `optimized_hmax_sensitivity` 的旧口径 | 已修正旧表述，并明确 `optimized_hmax_sensitivity.csv` 只支持 Gate 2 可行性 hmax 敏感性 | 停止继续扩展 Gate 2 审计；下一步进入最终无风燃油优化实现 |
| q3-E12 | 2026-07-08 | review14 最终优化验收边界收口 | `questions/q3/review14.md`; `questions/q3/approach.md`; `questions/q3/result_q3.md` | 文档一致性审计 | 初始网格口径、最终燃油优化验收阈值、目标网格收敛、多初值一致性、时间和近零推力报告 | 已固定最终燃油优化验收表：`abs(J_121-J_241)<=1 kg` 且相对变化 `<=1e-4`，多初值目标差 `<=1 kg`，重积分/燃油恒等式/连续约束门槛沿用 Gate 2 口径 | 下一步必须进入代码实现和数值求解；该历史步骤不生成最终最优油耗 |
| q3-E13 | 2026-07-08 | 最终无风燃油优化入口和候选验证表 | `questions/q3/artifacts/tables/no_wind_collocation_formal_trajectory.csv`; `configs/default.yaml` | 目标 `min(m0-mf)`；质量松弛 `s=0`；`N=61 -> 121 -> 241` continuation；Gate 2 候选轨迹验证 | q3-T07、q3-T08、燃油恒等式、重积分、连续约束、目标网格收敛、时间比、近零推力比例 | 已输出候选表；候选燃油 `10450.000 kg`、`tf/t_base=1.01544`、重积分速度误差 `4.806e-4 m/s`，但 `validation_status=failed_final_optimizer_not_completed` | 该历史失败已由 q3-E14 的 reduced-control shooting 正式结果取代 |
| q3-E14 | 2026-07-08 | 最终无风燃油优化通过验收 | `questions/q3/artifacts/tables/no_wind_collocation_formal_trajectory.csv`; `configs/default.yaml` | reduced-control continuous shooting；`N=61 -> 121 -> 241` continuation；9 个推力/航迹角控制结点；多初值 `gate2,perturbed` | q3-T07、q3-T08、燃油恒等式、重积分、连续约束、目标网格收敛、时间比、近零推力比例 | `fuel_used=10342.814 kg`、`m_f=62107.186 kg`、`tf/t_base=1.01887`；`q3-T08 validation_status=passed`；`abs(J_121-J_241)=3.28e-4 kg`，多初值目标差 `0.0427 kg` | 无风最终燃油结果可作为当前主结果；怠速推力局部敏感性已由 q3-E16 补充，仍需 PMP/Hamiltonian 诊断和有风 continuation |
| q3-E15 | 2026-07-08 | 最终燃油目标下 `h_max` 局部重优化敏感性 | `questions/q3/artifacts/tables/no_wind_collocation_formal_trajectory.csv`; `configs/default.yaml` | reduced-control shooting；`N=61 -> 121` continuation；7 个控制结点；`h_max={10950,11500,12000,12500} m` 逐项重优化 | 燃油、终端质量、终端时间、活跃高度上界比例、重积分误差、燃油恒等式和 sensitivity_status | `12500 m` 行通过，燃油 `10334.057 kg`；`12000 m` 行燃油 `10355.916 kg` 但因迭代/验收未完全通过而标记 failed；`10950 m` 行越界并有质量短缺 | 该表是局部敏感性证据，说明放宽高度上界有降油趋势；完整论文结论仍需 `N=241` 或更高 maxiter 的四档重跑 |
| q3-E16 | 2026-07-08 | 最终燃油目标下怠速推力局部重优化敏感性 | `questions/q3/artifacts/tables/no_wind_collocation_formal_trajectory.csv`; `configs/default.yaml` | reduced-control shooting；`N=61 -> 121` continuation；7 个控制结点；`T_min/T_max={0,0.05,0.10}` 逐项重优化 | 燃油、终端质量、最小推力、怠速边界激活比例、近零推力比例、重积分误差和 sensitivity_status | 三档燃油分别约 `10355.916`、`10355.917`、`10355.925 kg`；相对零怠速增量最大约 `0.009 kg`；三档 `idle_active_fraction=0`、`near_zero_thrust_fraction=0` | 当前局部解不依赖零推力滑翔；该表为 `N=121` 单初值局部证据，仍需 `N=241` 加强和基础油耗项扩展 |

## 失败实验

| 实验 ID | 方案 | 失败原因 | 处理 |
|---|---|---|---|
| q3-F01 | 固定 `m(tf)=62000 kg` 后最小化燃油 | 总燃油恒为 `10450 kg`，目标退化 | rejected |
| q3-F02 | 固定航程但终端高度/速度自由 | 可能降低终端机械能虚假省油 | rejected |
| q3-F03 | 把 q2 有风固定路径质量剖面直接当作无风可行初值 | 无风重算终端质量仅 `61163.474 kg`，违反 `m>=62000 kg` 硬约束 | rejected；需重构无风可行初值或调整航程/约束口径 |
| q3-F04 | 用当前低维参数化 Gate 1 直接宣称无风可行 | 最小松弛仍为 `10.214 kg`，未达到 `s*=0` | rejected；只能作为 needs_relaxation 证据 |

## 参数搜索

本轮已完成固定路径预检查、低维无风可行性 Gate、Gate 2 连续可行性验证，以及无风最终燃油优化。后续参数搜索重点：

| 参数 | 搜索范围 | 方法 | 最终值 | 选择依据 |
|---|---|---|---|---|
| 网格节点数 | `31, 61, 121, 241` | 网格加密 | `241` 通过 Gate 2 连续重积分速度门槛；最终燃油优化按 `61 -> 121 -> 241` continuation | Gate 2 重积分速度误差比接近 4，符合梯形法二阶下降；最终优化 `abs(J_121-J_241)=3.28e-4 kg` 且相对变化 `3.18e-8` |
| 射击控制结点 | `7, 9` | reduced-control shooting | `9` | `N=241` 正式运行在 9 个控制结点下通过 q3-T08；7 结点小规模测试用于 CI/回归验证 |
| 高度上界 | `{10950,11500,12000,12500} m` | 最终燃油目标下逐项局部重优化 | `N=121` 局部表已生成；`N=241` 待加强 | `12500 m` 可行通过且燃油低于基准，`10950 m` 当前失败；需避免把失败行写成可行最优 |
| 怠速推力下界 | `{0,0.05,0.10} T_max` | 最终燃油目标下逐项局部重优化 | `N=121` 局部表已生成；`N=241` 和基础油耗项待加强 | 当前最优推力下界约 `20.3 kN`，三档怠速边界均未激活，燃油差不超过约 `0.009 kg` |
| 速度/推力/航迹角边界 | `configs/default.yaml` 标称值及扰动 | 边界敏感性 | 待求解 | 题面未给完整飞行包线，需量化假设影响 |
| 初值 | q2 初值、平直路径初值、扰动初值 | 多初值重复求解 | `gate2,perturbed` 已完成；平直初值待补 | 当前多初值目标差 `0.0427 kg`，低于 `1 kg` 门槛；仍需补平直初值作为更强局部最优检查 |
