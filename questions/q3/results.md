# q3 结果与结论

## 1. 最终模型

- 当前状态：待优化求解。
- 本轮完成内容：题意审计、优化问题定义、PMP 必要条件推导、直接法求解方案设计。
- review1 后补充内容：求解器前固定路径可行性预检查。
- review2 后补充内容：无风可行性 Gate 初版。
- 主模型：固定航程、固定终端高度和速度、终端质量自由的点质量最优控制模型。
- 关键参数：`Xf=189781.310 m`，`h(tf)=10577.124 m`，`V(tf)=240 m/s`。

## 2. 核心结果

本轮不生成正式最优数值。

| 指标 / 输出 | 数值 | 单位 | 产物 | Claim ID |
|---|---:|---|---|---|
| 固定目标航程 | 189781.310 | m | `artifacts/q2/data/q2_fuel_summary.csv` | Q3-C01 |
| 终端参考高度 | 10577.124 | m | `artifacts/q1/data/constant_speed_profile.csv` | Q3-C02 |
| 终端参考速度 | 240.000 | m/s | `artifacts/q1/data/constant_speed_profile.csv` | Q3-C02 |
| 配置风场固定路径终端质量 | 62022.744 | kg | `questions/q3/artifacts/tables/baseline_feasibility.csv` | Q3-C04 |
| 无风固定路径终端质量 | 61163.474 | kg | `questions/q3/artifacts/tables/baseline_feasibility.csv` | Q3-C04 |
| 无风可行性 Gate 质量松弛 | 10.214 | kg | `questions/q3/artifacts/tables/no_wind_feasibility_gate.csv` | Q3-C05 |

## 3. 验证结果

本轮尚未运行最优控制求解，因此没有最优轨迹的动力学缺陷、约束余量或 Hamiltonian 残差数值。已完成固定路径预检查：

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

上述 `h_max` 表只表示 warm-start 诊断，不表示优化后的 `s*(h_max)`。正式 `optimized_hmax_sensitivity.csv` 仍需等待非 dry-run Gate 2 NLP。

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

review8 后新增非 dry-run Gate 2 一阶段 NLP。该步骤不是最终省油优化，只求解：

```text
min s
subject to m_f + s >= 62000, s >= 0
```

`N=31,h_max=12000 m` 结果：

| 方法 | 状态 | 终端质量 kg | 质量松弛 kg | 总时间 s | 尺度化配点缺陷 | 重积分质量误差 kg | 重积分速度误差 m/s |
|---|---|---:|---:|---:|---:|---:|---:|
| 航程域梯形 collocation Gate 2 stage1 | needs_relaxation | 62000.000 | 2.48e-12 | 802.951 | 1.42e-14 | 0.704 | 0.0302 |

解释：离散 NLP 等式和终端质量松弛已经满足，但独立 ODE 重积分仍未达到正式门槛，因此不能写成严格可行轨迹。下一步应做网格加密、连续重构或更高阶转录，而不是进入最终燃油最优。

## 4. 灵敏度与稳健性

计划在第二轮实现中检查：

- 网格节点数敏感性；
- 高度、速度、马赫数、推力、航迹角和控制变化率边界敏感性；
- q2 初值、平直初值和扰动初值；
- 无风解到有风解的 continuation。
- 自由终端时间运营约束对照，例如 `tf<=1.05 t_base`、`tf<=1.10 t_base` 或时间加权目标。
- `T_min`/怠速推力敏感性和风场高度边界敏感性。
- 可行性 Gate 的参数化阶数、节点数和多初值敏感性。
- 完整 collocation 可行性 Gate 的 `h_max` 敏感性和 11 km 大气平滑方案敏感性。

## 5. 可写入论文的结论

当前只能写入模型设计和前置可行性结论，不能写入最优数值结论：

第三问应构造为固定航程、终端质量自由的最优控制问题。为避免虚假省油，主方案固定终端高度和速度；推力与航迹角作为控制量，高度和速度作为状态轨迹。直接配点法适合作为主求解方法，PMP 必要条件用于结果诊断。

在 `Xf=189781.310 m` 下，q1 等速固定路径在配置风场中仍满足 `m>=62000 kg`，但在无风下不满足该硬约束。因此不能把 q2 有风质量剖面直接作为无风优化的可行基线。

当前无风可行性 Gate 的最小质量松弛为 `10.214 kg`，状态为 `needs_relaxation`。下一步应扩展为完整 collocation 可行性 NLP 或增加多初值/参数化自由度；只有 `s*≈0` 时，才可进入无风最优轨迹求解。

这里的 `s*≈0` 按预设门槛定义为：质量缺口 `<=0.05 kg`、尺度化配点缺陷无穷范数 `<=1e-6`、终端高度误差 `<=0.1 m`、终端空速误差 `<=1e-3 m/s`，且非松弛状态/控制约束的无量纲违反不超过 `1e-6`。词典序第二阶段的松弛容差为 `epsilon_s=1e-3 kg`。在达到该门槛前，不得写入无风正式最优油耗。

review7 后该门槛进一步明确：若第一阶段达到 `s_min=0`，第二阶段不得重新允许 `s<=1e-3 kg` 造成硬质量约束违反；应固定 `s=0` 或施加 `m_f>=62000-epsilon_num`。正式 Gate 2 同时需要独立 ODE 重积分误差和节点间重构检查。

## 6. 局限与适用范围

- 本轮没有生成最优轨迹或最优油耗。
- 题面未给完整飞行包线，边界值属于仿真假设，必须做敏感性分析。
- q2 基线可作为初值和比较对象，但不是最优解。
- q2 基线只在配置风场固定路径预检查中可行；无风问题需要重新构造可行初值。
- 有风问题可能存在局部最优，需要无风初值和多初值检查。
- 当前燃油模型允许 `T=0` 时零燃油流量，正式优化结果必须解释该简化或引入怠速推力/基础油耗敏感性。
- Gate 1 是低维参数化可行性搜索，不是全局可行性证明；`needs_relaxation` 不能被写成“问题不可行”。

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

主求解脚本仍为 scaffold：

```bash
python questions/q3/scripts/pipeline.py --dry-run
```
