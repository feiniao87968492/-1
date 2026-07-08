# q3 结果与结论

## 1. 最终模型

- 当前状态：Gate 2 连续一致性已通过；无风最终燃油优化已通过 q3-T08 验收。
- 本轮完成内容：题意审计、优化问题定义、PMP 必要条件推导、直接法求解方案设计、非 dry-run Gate 2 Stage 1 可行性 NLP、reduced-control shooting 无风最终燃油优化，以及最终燃油目标下的 `h_max` 和怠速推力局部重优化敏感性。
- review1 后补充内容：求解器前固定路径可行性预检查。
- review2 后补充内容：无风可行性 Gate 初版。
- review9 后补充内容：正式 Gate 2 重积分有符号诊断、分段线性控制重构说明和优化后 `h_max` 连续诊断。
- review11 后补充内容：`N=241` 网格可行性、ODE 容差敏感性和沿程连续约束审计。
- 主模型：固定航程、固定终端高度和速度、终端质量自由的点质量最优控制模型。
- 关键参数：`Xf=189781.310 m`，`h(tf)=10577.124 m`，`V(tf)=240 m/s`。

## 2. 核心结果

本轮生成通过验收的无风最终燃油优化数值，并补充了最终燃油目标下的 `h_max` 和怠速推力局部重优化敏感性。Q3 整体仍未标记为 `done`，因为这些敏感性仍需 `N=241` 加强，基础油耗项、PMP/Hamiltonian 诊断和有风 continuation 仍待补充。

| 指标 / 输出 | 数值 | 单位 | 产物 | Claim ID |
|---|---:|---|---|---|
| 固定目标航程 | 189781.310 | m | `artifacts/q2/data/q2_fuel_summary.csv` | Q3-C01 |
| 终端参考高度 | 10577.124 | m | `artifacts/q1/data/constant_speed_profile.csv` | Q3-C02 |
| 终端参考速度 | 240.000 | m/s | `artifacts/q1/data/constant_speed_profile.csv` | Q3-C02 |
| 配置风场固定路径终端质量 | 62022.744 | kg | `questions/q3/artifacts/tables/baseline_feasibility.csv` | Q3-C04 |
| 无风固定路径终端质量 | 61163.474 | kg | `questions/q3/artifacts/tables/baseline_feasibility.csv` | Q3-C04 |
| 无风可行性 Gate 质量松弛 | 10.214 | kg | `questions/q3/artifacts/tables/no_wind_feasibility_gate.csv` | Q3-C05 |
| Gate 2 `N=241` 质量松弛 | 5.89e-13 | kg | `questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv` | Q3-C14 |
| Gate 2 `N=241` 尺度化配点缺陷 | 5.97e-16 | 1 | `questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv` | Q3-C14 |
| Gate 2 `N=241` 重积分速度误差 | 4.806e-4 | m/s | `questions/q3/artifacts/tables/no_wind_collocation_formal_gate.csv` | Q3-C14 |
| Gate 2 `N=241` 连续约束违反 | 0.000 | 1 | `questions/q3/artifacts/tables/no_wind_collocation_continuous_audit.csv` | Q3-C14 |
| q3-T07 无风最终燃油 | 10342.814 | kg | `questions/q3/artifacts/tables/no_wind_final_optimal_results.csv` | Q3-C16 |
| q3-T07 终端质量 | 62107.186 | kg | `questions/q3/artifacts/tables/no_wind_final_optimal_results.csv` | Q3-C16 |
| q3-T07 终端时间比 `tf/t_base` | 1.01887 | 1 | `questions/q3/artifacts/tables/no_wind_final_optimal_validation.csv` | Q3-C16 |
| q3-T08 验证状态 | `passed` | - | `questions/q3/artifacts/tables/no_wind_final_optimal_validation.csv` | Q3-C16 |
| q3-T09 `h_max=12500 m` 局部重优化燃油 | 10334.057 | kg | `questions/q3/artifacts/tables/no_wind_final_hmax_sensitivity.csv` | Q3-C17 |
| q3-T10 `T_min=0.10T_max` 局部重优化燃油 | 10355.925 | kg | `questions/q3/artifacts/tables/no_wind_final_idle_thrust_sensitivity.csv` | Q3-C18 |

## 3. 验证结果

当前已运行无风最终燃油优化并通过 q3-T08 验收。Hamiltonian/PMP 残差仍未形成正式表格，后续需补充；因此下表只支持数值可行性、目标收敛和多初值一致性，不支持完整 PMP 最优性证明。

| 检查项 | 阈值 / 输出要求 | 说明 |
|---|---:|---|
| 重积分终端速度误差 | `<=1e-3 m/s` | 沿用 Gate 2 连续速度门槛 |
| 重积分终端高度误差 | `<=0.1 m` | 沿用 Gate 2 终端高度门槛 |
| 连续路径约束违反 | `<=1e-6` 无量纲 | 高度、速度、马赫、推力、航迹角和质量下限均需检查 |
| 燃油恒等式残差 | `<=0.05 kg` | 检查质量亏损与积分油耗一致性 |
| 目标网格收敛 | `abs(J_121-J_241)<=1 kg` 且相对变化 `<=1e-4` | 检查燃油目标值，而非只检查可行性 |
| 多初值目标差 | `max(J)-min(J)<=1 kg` | 至少比较 Gate 2 初值、平直/等速初值和扰动初值 |
| 近零推力比例 | 报告，不设硬阈值 | 用于解释 `T_min=0` 的模型偏差 |
| 时间比 | 报告 `tf/t_base`，并做 `1.05/1.10` 约束对照 | 无风固定路径时间基准 `t_base=790.755 s` |
| 求解器最优性/KKT | 报告 | 至少记录 success/message、最大约束违反和可用的最优性或 KKT proxy |

q3-T08 当前验证结果：

| 验证项 | 数值 | 阈值 | 状态 |
|---|---:|---:|---|
| 重积分终端速度误差 | `1.71e-5 m/s` | `<=1e-3` | passed |
| 重积分终端高度误差 | `3.62e-4 m` | `<=0.1` | passed |
| 连续路径约束违反 | `0` | `<=1e-6` | passed |
| 燃油恒等式残差 | `8.58e-5 kg` | `<=0.05` | passed |
| 目标网格收敛 `abs(J_121-J_241)` | `3.28e-4 kg` | `<=1` | passed |
| 目标相对变化 | `3.18e-8` | `<=1e-4` | passed |
| 多初值目标差 | `0.0427 kg` | `<=1` | passed |
| 近零推力比例 | `0` | 报告 | reported |
| 时间比 `tf/t_base` | `1.01887` | `<=1.05/1.10` 对照 | passed |

已完成固定路径预检查：

| 风场 | 总时间 s | 总燃油 kg | 终端质量 kg | 质量约束 | 基线可行 |
|---|---:|---:|---:|---|---|
| 配置风场 | 721.753 | 10427.256 | 62022.744 | 满足 | 是 |
| 无风 | 790.755 | 11286.526 | 61163.474 | 不满足 | 否 |

结论：q2 有风固定路径基线不是无风 q3 问题的可行初值。正式求解器实现前，需要先构造无风可行轨迹、缩短无风固定航程，或经确认后调整 `m>=62000 kg` 约束口径。

review2 后新增无风可行性 Gate；review3 后修正字段解释：

| 方法 | 状态 | 终端质量 kg | 质量缺口 kg | 总时间 s | 非松弛约束最大违反 | 积分一致性残差 |
|---|---|---:|---:|---:|---:|---:|
| 固定 q1 路径 | 不可行 | 61163.474 | 836.526 | 790.755 | 0.000 | 0.000 |
| 航程域参数化 Gate 1 | needs_relaxation | 61989.786 | 10.214 | 802.883 | 0.000 | 6.94e-18 |

该结果说明可行性搜索显著缩小了质量缺口，但尚未达到 `s*=0`。因此不能进入正式无风最优求解，也不能据此证明整个无风问题不可行。

Gate 1 采用的配置边界和轨迹诊断：

| 指标 | 配置边界 | Gate 1 轨迹范围 / 余量 |
|---|---:|---:|
| 高度 | `[9000, 12000] m` | `[9500.000, 12000.000] m`，最小余量 `2.98e-05 m` |
| 空速 | `[210, 270] m/s` | `[234.373, 240.000] m/s`，最小余量 `24.373 m/s` |
| 推力 | `[0, 90000] N` | `[25647.548, 72018.170] N`，最小余量 `17981.830 N` |
| 航迹角 | `|gamma|<=0.05236 rad` | `[-0.026406, 0.037501] rad`，最小余量 `0.014859 rad` |
| 马赫数 | `M<=0.84` | 最大 `0.808724`，余量 `0.031276` |
| 升力系数 | 诊断量 | `[0.489343, 0.667625]` |

高度上界几乎激活，后续完整 collocation 和敏感性分析应优先检查 `h_max`。Gate 1 的最小推力远大于零，说明该接近可行轨迹没有依赖零推力滑翔。

review3(2) 后的解释边界：

- 当前 `s*=10.214 kg` 是在 `h_max=12000 m` 且当前分层 ISA 数值函数下得到的低维 Gate 结论。
- 由于 Gate 1 几乎贴住 `h_max`，该质量缺口不能简单解释为算法自由度不足；也可能是高度上界限制了可行性。
- 完整 collocation 前必须处理 11 km 大气层导数问题。默认采用 `10950-11050 m` 的 `C1` 平滑过渡；若改为 `h_max<=10950 m`，需作为单独对流层内方案报告。
- 后续 Gate 2 必须比较 `h_max={10950,11500,12000,12500} m`，报告 `s*(h_max)`、终端质量、终端时间和活跃约束。

review4 后新增 Gate 2 dry-run/readiness 产物。该步骤只将 Gate 1 轨迹投影到 C1 平滑大气模型并计算配点诊断，不执行可行性优化：

| 方法 | 状态 | 终端质量 kg | 质量缺口 kg | 总时间 s | 最大无量纲约束违反 | 尺度化配点缺陷 | 中点高度越界 m |
|---|---|---:|---:|---:|---:|---:|---:|
| 航程域 collocation dry-run | dry_run_not_optimized | 61985.803 | 14.197 | 802.859 | 0.000 | 6.20e-05 | 0.000 |

平滑大气采用 `C1_temperature_hydrostatic_pressure`：只平滑温度曲线，压力由静力方程积分，密度和声速由状态方程计算。在 `10900-11100 m` 审计区间内，相对精确分层 ISA 的最大偏差为：温度 `0.08125 K`、压力 `0.044253 Pa`、密度 `1.36e-4 kg/m^3`。这些数值只用于进入完整 Gate 2 优化前的模型一致性审计。

review5 后新增 dry-run 证据表：

| 诊断 | 结果 | 产物 |
|---|---:|---|
| Gate 1 原轨迹终端质量 | 61989.785554 kg | `questions/q3/artifacts/tables/gate1_to_collocation_projection_audit.csv` |
| 插值到 Gate 2 网格并按原分层 ISA 重推后的终端质量 | 61985.803328 kg | `questions/q3/artifacts/tables/gate1_to_collocation_projection_audit.csv` |
| C1 大气投影相对原分层 ISA 投影的质量差异 | 0.000000 kg | `questions/q3/artifacts/tables/gate1_to_collocation_projection_audit.csv` |
| C1 大气最大静力残差 | 2.22e-16 | `questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv` |
| `h_max=10950 m` warm-start 高度越界 | 1050.000 m | `questions/q3/artifacts/tables/warm_start_hmax_diagnostic.csv` |

上述 `h_max` 表只表示 warm-start 诊断，不表示优化后的 `s*(h_max)`。review8 后已另行生成 Gate 2 可行性优化后的 `optimized_hmax_sensitivity.csv`，并在 review9 后补充每行连续重积分诊断。该表仍只服务于可行性 Gate，不等于最终燃油最优条件下的高度上界敏感性。

review6 后新增代码级 C1 大气耦合与独立静力残差诊断：

| 诊断 | 数值 | 产物 |
|---|---:|---|
| C1 相对分层 ISA 密度差（11000 m 固定状态点） | -1.3607e-4 kg/m^3 | `questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv` |
| C1 相对分层 ISA 阻力差 | -2.843 N | `questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv` |
| C1 相对分层 ISA `dV/dx` 差 | 1.8058e-7 1/m | `questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv` |
| C1 相对分层 ISA `dm/dx` 差 | 0.000 kg/m | `questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv` |
| 有限差分静力残差最大值 | 1.1943e-08 | `questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv` |
| 有限差分静力残差 RMS | 2.0985e-09 | `questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv` |

解释：C1 大气已经进入密度、阻力和 `dV/dx` 链路；但当前 warm start 使用固定推力 mass-rate，`dm/dx=-c_T T Phi(V)/V_g`，在该固定状态点不直接含密度或阻力，因此 B 到 C 终端质量差为 0 不能写成物理普遍结论，只能写成当前投影口径下的模型结构结果。

review7 后新增 required-thrust 燃油耦合诊断和静力残差步长敏感性：

| 诊断 | 数值 | 产物 |
|---|---:|---|
| 固定 `dV/dx=5.0e-4 1/m` 时 C1 相对分层 ISA 所需推力差 | -2.843 N | `questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv` |
| required-thrust 口径下 C1 相对分层 ISA `dm/dx` 差 | 3.3877e-06 kg/m | `questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv` |
| 无量纲有限差分静力残差步长敏感性最大值范围 | 4.7506e-10 到 1.1944e-06 | `questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv` |

解释：固定推力下质量率差仍为 `0`，但当推力由目标速度梯度和阻力一致反算时，大气差异会通过 `D -> T_required -> dm/dx` 进入燃油率。该结论仍是固定状态诊断，不是非 dry-run Gate 2 NLP 的最优燃油证据。正式 Gate 2 还必须报告独立 ODE 重积分误差，不能只使用 `scaled_collocation_defect_inf`。

review8 后新增非 dry-run Gate 2 一阶段 NLP。review9 后补充连续重积分的有符号诊断和更准确状态命名。该步骤不是最终省油优化，只求解：

```text
min s
subject to m_f + s >= 62000, s >= 0
```

`N=31,h_max=12000 m` 结果：

| 方法 | 状态 | 终端质量 kg | 质量松弛 kg | 总时间 s | 尺度化配点缺陷 | 重积分终端质量 kg | 重积分速度误差 m/s |
|---|---|---:|---:|---:|---:|---:|---:|
| 航程域梯形 collocation Gate 2 stage1 | discrete_feasible_reintegration_failed | 62000.000 | 2.48e-12 | 802.951 | 1.42e-14 | 62000.704 | 0.0302 |

重积分控制重构口径为 `piecewise_linear_node_controls`。重积分相对离散终端质量的有符号误差为 `+0.703760 kg`，连续质量短缺为 `0 kg`；终端高度有符号误差为 `-0.000994 m`，终端速度有符号误差为 `+0.030218 m/s`。解释：离散 NLP 等式和终端质量松弛已经满足，但独立 ODE 重积分速度误差未达到正式门槛，因此不能写成严格可行轨迹。下一步应做 `N=61/121` 网格收敛、连续重构或更高阶转录，而不是进入最终燃油最优。

优化后 `h_max` 敏感性表当前结果：

| h_max m | 质量松弛 kg | 重积分质量短缺 kg | 重积分速度误差 m/s | 活跃高度上界比例 | gate_status |
|---:|---:|---:|---:|---:|---|
| 10950 | 0.000 | 0.000 | 0.00568 | 0.258 | discrete_feasible_reintegration_failed |
| 11500 | 0.000 | 0.000 | 0.02756 | 0.097 | discrete_feasible_reintegration_failed |
| 12000 | 2.48e-12 | 0.000 | 0.03022 | 0.000 | discrete_feasible_reintegration_failed |
| 12500 | 2.48e-12 | 0.000 | 0.03022 | 0.000 | discrete_feasible_reintegration_failed |

该表说明四个高度上界方案都能达到离散质量松弛数值零，但没有一个通过连续重积分速度门槛；因此仍不能作为 Gate 2 通过或最终最优结论。

review10 后新增 `h_max=12000 m` 基准方案的网格收敛诊断：

| N | 重积分质量误差 kg | 重积分速度误差 m/s | 质量误差比 | 速度误差比 | 最大推力步长 N | 最大航迹角步长 rad | gate_status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 31 | 0.703760 | 0.030218 |  |  | 2270.082 | 0.003321 | discrete_feasible_reintegration_failed |
| 61 | 0.174045 | 0.007656 | 4.044 | 3.947 | 1132.807 | 0.001662 | discrete_feasible_reintegration_failed |
| 121 | 0.045053 | 0.001897 | 3.863 | 4.035 | 566.110 | 0.000831 | discrete_feasible_reintegration_failed |

该表保存于 `questions/q3/artifacts/tables/no_wind_collocation_mesh_convergence.csv`。误差比接近 4，说明 review10 阶段的失败主要符合梯形配点与分段线性控制重构的网格误差特征；当时 `N=121` 的终端速度重积分误差仍为 `0.001897 m/s`，高于 `1e-3 m/s` 门槛，因此尚不能进入最终无风燃油最优。该历史限制已由 review11 的 `N=241` 结果更新。

review11 后将基准网格扩展到 `N=241`，并新增 ODE 容差敏感性和沿程连续路径审计：

| N | 重积分质量误差 kg | 重积分速度误差 m/s | 质量误差比 | 速度误差比 | gate_status |
|---:|---:|---:|---:|---:|---|
| 31 | 0.703760 | 0.030218 |  |  | discrete_feasible_reintegration_failed |
| 61 | 0.174045 | 0.007656 | 4.044 | 3.947 | discrete_feasible_reintegration_failed |
| 121 | 0.045053 | 0.001897 | 3.863 | 4.035 | discrete_feasible_reintegration_failed |
| 241 | 0.010663 | 0.000481 | 4.225 | 3.948 | gate2_feasible |

`N=241` 的离散质量松弛约 `5.89e-13 kg`，尺度化配点缺陷约 `5.97e-16`，连续重积分终端高度误差约 `3.25e-5 m`，终端速度误差约 `4.806e-4 m/s`，连续约束无量纲违反为 `0`。因此 Gate 2 可行性门槛已通过。

ODE 容差敏感性表保存于 `questions/q3/artifacts/tables/no_wind_collocation_reintegration_tolerance.csv`。在同一条 `N=241` 控制轨迹上，`rtol=1e-8,1e-10,1e-12` 的终端速度有符号误差分别约为 `4.807e-4`、`4.775e-4`、`4.780e-4 m/s`，相邻差异最大约 `3.22e-6 m/s`，远低于 `1e-4 m/s` 容差稳定性检查口径。

沿程连续路径审计表保存于 `questions/q3/artifacts/tables/no_wind_collocation_continuous_audit.csv`。严格容差下最大高度重构误差约 `0.041 m`，最大速度重构误差约 `0.00114 m/s`，最大质量重构误差约 `0.0501 kg`，最大尺度化状态误差约 `4.73e-6`；高度、速度、马赫、推力和航迹角连续约束违反均为 `0`。

## 4. 灵敏度与稳健性

已完成基准 `h_max=12000 m` 的 `N=31/61/121/241` Gate 2 网格收敛诊断，且 `N=241` 通过连续重积分门槛。无风最终燃油优化采用 `N=61->121->241` reduced-control shooting continuation，`q3-T08` 已通过。

最终燃油目标下的 `h_max` 局部重优化敏感性表保存于 `questions/q3/artifacts/tables/no_wind_final_hmax_sensitivity.csv`。本轮采用 `N=61->121` continuation、7 个控制结点和单初值，结论强度低于 q3-T07/q3-T08 主结果：

| h_max m | 燃油 kg | 终端质量 kg | 最大高度 m | 活跃上界比例 | sensitivity_status |
|---:|---:|---:|---:|---:|---|
| 10950 | 10459.671 | 61990.329 | 10996.063 | 0.0083 | failed |
| 11500 | 10403.972 | 62046.028 | 11499.965 | 0.0496 | failed |
| 12000 | 10355.916 | 62094.084 | 11999.961 | 0.0248 | failed |
| 12500 | 10334.057 | 62115.943 | 12352.720 | 0.0000 | passed |

解释：该表说明在当前局部参数化下，放宽高度上界具有降低燃油的趋势；但除 `12500 m` 外，其余行未完全通过当前验收或存在高度/质量问题，不能写成可行最优结论。

最终燃油目标下的怠速推力局部重优化敏感性表保存于 `questions/q3/artifacts/tables/no_wind_final_idle_thrust_sensitivity.csv`。本轮采用 `N=61->121` continuation、7 个控制结点和单初值：

| T_min/T_max | T_min N | 燃油 kg | 燃油增量 kg | 最小推力 N | 怠速激活比例 | 近零推力比例 | sensitivity_status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 0.00 | 0 | 10355.916 | 0.000 | 20286.815 | 0.0000 | 0.0000 | failed |
| 0.05 | 4500 | 10355.917 | 0.001 | 20286.056 | 0.0000 | 0.0000 | failed |
| 0.10 | 9000 | 10355.925 | 0.009 | 20291.293 | 0.0000 | 0.0000 | failed |

解释：当前局部解的最小推力约 `20.3 kN`，明显高于 `0.10T_max=9 kN`，因此三档怠速下界均未激活，燃油变化很小。这支持“当前无风局部最优不依赖零推力滑翔”的阶段性判断；但该表仍是 `N=121` 单初值局部证据，且 `sensitivity_status` 未全部通过，不能替代 `N=241` 加强或基础油耗项扩展。

后续仍需检查：

- 高度、速度、马赫数、推力、航迹角和控制变化率边界敏感性；
- q2 初值、平直初值和扰动初值；当前已比较 Gate 2 初值和扰动初值，平直初值待补。
- 无风解到有风解的 continuation。
- 自由终端时间运营约束对照，例如 `tf<=1.05 t_base`、`tf<=1.10 t_base` 或时间加权目标。
- `N=241` 或更高迭代的最终燃油 `h_max` 和怠速推力敏感性加强，以及基础油耗项敏感性。
- 可行性 Gate 的参数化阶数、节点数和多初值敏感性。
- 更高阶/局部加密 collocation、Stage 1B 控制平滑和 11 km 大气平滑方案敏感性。

## 5. 可写入论文的结论

当前可以写入模型设计、前置可行性结论和无风最终燃油优化数值结论；暂不能写入有风最优结论或 PMP/Hamiltonian 完整最优性诊断。

第三问应构造为固定航程、终端质量自由的最优控制问题。为避免虚假省油，主方案固定终端高度和速度；推力与航迹角作为控制量，高度和速度作为状态轨迹。直接配点法适合作为主求解方法，PMP 必要条件用于结果诊断。

在 `Xf=189781.310 m` 下，q1 等速固定路径在配置风场中仍满足 `m>=62000 kg`，但在无风下不满足该硬约束。因此不能把 q2 有风质量剖面直接作为无风优化的可行基线。

当前非 dry-run Gate 2 Stage 1 的离散质量松弛已达到数值零，`N=31/61/121/241` 网格收敛显示重积分误差按约二阶下降，且 `N=241` 通过连续重积分速度门槛。以该可行轨迹为初值，reduced-control shooting 最终无风燃油优化得到 `J=10342.814 kg`、`m_f=62107.186 kg`、`tf=805.679 s`，相对 Gate 2 可行候选 `10450.000 kg` 降低约 `107.186 kg`。

这里的 Gate 2 通过门槛定义为：离散质量缺口 `<=0.05 kg`、尺度化配点缺陷无穷范数 `<=1e-6`、连续重积分终端高度误差 `<=0.1 m`、终端空速误差 `<=1e-3 m/s`，且离散和连续重构约束的无量纲违反不超过 `1e-6`。词典序第二阶段的松弛容差为 `epsilon_s=1e-3 kg`。在达到该门槛前，不得写入无风正式最优油耗。

最终无风优化固定 `s=0`，并由 q3-T08 检查终端质量下限、独立 ODE 重积分误差、燃油恒等式、连续约束、目标网格收敛和多初值一致性。当前验证状态为 `passed`。

## 6. 局限与适用范围

- 本轮已生成无风最终最优轨迹和最优油耗；非 dry-run Gate 2 Stage 1 只用于可行性门控和最终燃油优化初值。
- 题面未给完整飞行包线，边界值属于仿真假设，必须做敏感性分析。
- q2 基线可作为初值和比较对象，但不是最优解。
- q2 基线只在配置风场固定路径预检查中可行；无风问题需要重新构造可行初值。
- 有风问题可能存在局部最优，需要无风初值和多初值检查。
- 当前燃油模型允许 `T=0` 时零燃油流量；本次无风最优结果近零推力比例为 `0`，且 `N=121` 怠速推力局部敏感性显示三档怠速下界均未激活，但仍需 `N=241` 加强和基础油耗项敏感性。
- Gate 1 是低维参数化可行性搜索，不是全局可行性证明；Gate 2 Stage 1 的 `N=241` 结果只能写成“连续可行的可行性初值”，最终燃油最优结论应引用 q3-T07/q3-T08。
- `optimized_hmax_sensitivity.csv` 是 Gate 2 Stage 1 可行性敏感性表；最终燃油敏感性应引用 `no_wind_final_hmax_sensitivity.csv`，但该表当前仍是 `N=121` 单初值局部重优化证据，需要 `N=241` 加强后才能作为强论文结论。

## 7. 复现命令

预检查脚本：

```bash
python questions/q3/scripts/precheck.py --config configs/default.yaml
```

无风可行性 Gate：

```bash
python questions/q3/scripts/solve_feasibility_no_wind.py --config configs/default.yaml --nodes 21
```

无风 collocation Gate dry-run：
```bash
python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 21 --dry-run
```

无风 collocation Gate 非 dry-run 一阶段 NLP：
```bash
python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 31
```

无风 collocation Gate `N=241`、网格收敛、ODE 容差和连续审计：
```bash
python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 241 --mesh-study-nodes 31,61,121,241 --skip-hmax-sensitivity --ode-rtols 1e-8,1e-10,1e-12
```

无风最终燃油优化：

```bash
python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --final-fuel --final-solver shooting --nodes 241 --continuation-nodes 61,121,241 --shooting-control-knots 9 --initial-guess gate2 --multi-initial-guesses gate2,perturbed --final-maxiter 120
```

最终燃油 `h_max` 局部敏感性：

```bash
python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --final-fuel --final-solver shooting --final-hmax-sensitivity --nodes 121 --continuation-nodes 61,121 --shooting-control-knots 7 --initial-guess gate2 --multi-initial-guesses gate2 --final-maxiter 80
```

最终燃油怠速推力局部敏感性：

```bash
python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --final-fuel --final-solver shooting --final-idle-thrust-sensitivity --final-idle-thrust-fractions 0,0.05,0.10 --nodes 121 --continuation-nodes 61,121 --shooting-control-knots 7 --initial-guess gate2 --multi-initial-guesses gate2 --final-maxiter 120
```

主求解脚本仍为 scaffold：

```bash
python questions/q3/scripts/pipeline.py --dry-run
```
