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
| q3-E07 | 2026-07-07 | review8 非 dry-run Gate 2 无风可行性 NLP | `questions/q3/artifacts/tables/no_wind_feasibility_trajectory.csv`; `configs/default.yaml` | 航程域梯形配点；一阶段目标 `min s`；SLSQP；独立 ODE 重积分 | 质量松弛、配点缺陷、状态/控制约束违反、重积分终端误差、优化后 `h_max` 敏感性 | `N=31` 下 `s=2.48e-12 kg`、配点缺陷 `1.42e-14`、约束违反 `0`；但重积分质量误差 `0.704 kg`、速度误差 `0.0302 m/s`，状态 `needs_relaxation` | 非 dry-run 求解链路可运行，但未通过连续 ODE 重积分门槛；不能进入最终最优燃油求解 |

## 失败实验

| 实验 ID | 方案 | 失败原因 | 处理 |
|---|---|---|---|
| q3-F01 | 固定 `m(tf)=62000 kg` 后最小化燃油 | 总燃油恒为 `10450 kg`，目标退化 | rejected |
| q3-F02 | 固定航程但终端高度/速度自由 | 可能降低终端机械能虚假省油 | rejected |
| q3-F03 | 把 q2 有风固定路径质量剖面直接当作无风可行初值 | 无风重算终端质量仅 `61163.474 kg`，违反 `m>=62000 kg` 硬约束 | rejected；需重构无风可行初值或调整航程/约束口径 |
| q3-F04 | 用当前低维参数化 Gate 1 直接宣称无风可行 | 最小松弛仍为 `10.214 kg`，未达到 `s*=0` | rejected；只能作为 needs_relaxation 证据 |

## 参数搜索

本轮已完成固定路径预检查和低维无风可行性 Gate；尚未做正式最优数值优化。正式求解阶段计划：

| 参数 | 搜索范围 | 方法 | 最终值 | 选择依据 |
|---|---|---|---|---|
| 网格节点数 | `31, 61, 121` | 网格加密 | 待求解 | 检查最优目标和约束残差稳定性 |
| 高度/速度/推力/航迹角边界 | `configs/default.yaml` 标称值及扰动 | 边界敏感性 | 待求解 | 题面未给完整飞行包线，需量化假设影响 |
| 初值 | q2 初值、平直路径初值、扰动初值 | 多初值重复求解 | 待求解 | 检查局部最优风险 |
