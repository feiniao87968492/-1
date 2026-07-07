# q3 解法方案

## 1. 题意解释

- 原题要求：建立给定初始飞行状态下以总燃油消耗最小为目标的最优巡航策略模型，确定最优高度-速度联合变化规律，导出必要条件，并设计无风和有风条件下的数值求解方案。
- 数学目标：固定航程 `Xf=189781.310 m`，固定终端高度和速度，最大化终端质量 `m(tf)`。
- 输入：题面气动/发动机参数、q1 等速参考路径、q2 共同可行航程、`configs/default.yaml`。
- 输出：本轮输出优化问题定义、PMP 必要条件、直接法转录方案、验证计划和风险清单；不输出正式最优数值。
- 评价指标：边界条件满足、动力学缺陷、状态/控制约束余量、燃油积分与质量亏损一致、网格敏感性、Hamiltonian 诊断、相对 q2 基线是否改进。
- 歧义与采用解释：高度和速度作为状态轨迹；控制量为推力 `T(t)` 和航迹角 `gamma(t)`；固定终端高度/速度以避免用降低机械能换取虚假省油。

## 2. 符号、单位和约束

| 符号 | 含义 | 单位 | 范围 / 约束 |
|---|---|---|---|
| `x(t)` | 地面航程 | m | `0` 到 `Xf` |
| `h(t)` | 高度 | m | `h_min <= h <= h_max` |
| `V(t)` | 真空速 | m/s | `V_min <= V <= V_max` |
| `m(t)` | 质量 | kg | `m(tf)>=62000`；在 `T>=0` 且 `Phi(V)>0` 时质量单调下降，终端约束即可保证全程不低于该值 |
| `T(t)` | 推力 | N | `T_min <= T <= T_max` |
| `gamma(t)` | 航迹角 | rad | `|gamma|<=gamma_max` |
| `M(t)` | 马赫数 | 1 | `V/a(h)<=M_max` |
| `tf` | 终端时间 | s | 自由，正值 |
| `Phi(V)` | 速度惩罚项 | 1 | `1+beta(V-Vopt)^2` |

建议边界写入 `configs/default.yaml` 的 `q3_optimal_control` 段；当前文档先列为仿真假设，不在脚本中散落硬编码。第一版把 `m(tf)>=62000 kg` 作为终端硬约束；若无风问题在固定航程下不可行，不能静默降级为参考值，必须更新决策记录和证据链。

## 3. 数据与预处理

- 数据来源：`question.md`、`artifacts/q1/data/constant_speed_profile.csv`、`artifacts/q2/data/q2_fuel_summary.csv`。
- 质量问题：题面未给完整飞行包线、推力包线和控制变化率限制；必须记录为仿真假设并做敏感性。
- 缺失值：无观测数据。
- 异常值：风场采用用户确认 `W(h)=20+3e-5(h-10000)^2`。
- 单位与尺度：全部使用 SI 单位，角度内部用 rad。
- 防止泄漏：本问为优化模型，不涉及数据训练。

## 4. 基线方案

- 方法：沿 q1 等速几何路径分别重算配置风场和无风固定路径质量积分。
- 预检查脚本：`python questions/q3/scripts/precheck.py --config configs/default.yaml`。
- 配置风场基线：`Xf=189781.310 m`、`J=10427.256 kg`、`m(tf)=62022.744 kg`，满足 `m>=62000 kg`。
- 无风固定路径基线：`Xf=189781.310 m`、`J=11286.526 kg`、`m(tf)=61163.474 kg`，不满足 `m>=62000 kg`。
- 处理结论：q2 有风基线只能作为有风固定路径比较口径；不能直接作为无风优化问题的可行初值。正式无风最优求解前，必须先运行无风可行性 Gate；只有当质量松弛 `s*≈0` 时，才进入真正的无风最优求解。

## 5. 候选模型

| 模型 | 适配性 | 假设 | 优点 | 风险 | 是否采用 |
|---|---|---|---|---|---|
| 固定终止质量最小油耗 | 不适合 | `m(tf)=62000` | 与 q1 题设一致 | 目标退化为常数 | rejected |
| 固定航程、终端高度/速度自由 | 不足 | 只约束距离 | 省约束 | 可能降低机械能虚假省油 | rejected |
| 固定航程、固定终端高度/速度 | 适合 | 终端机械状态固定 | 公平比较油耗 | 约束更强，求解更难 | adopted |
| 终端能量高度约束 | 可作为扩展 | 只固定 `h+V^2/(2g)` | 可减少约束 | 高度/速度组合仍可能受风和马赫限制影响 | deferred |

## 6. 主模型

状态变量：

```text
z=(x,h,V,m)
```

控制变量：

```text
u=(T,gamma)
```

动力学：

```text
dx/dt = V cos(gamma) + W(h)
dh/dt = V sin(gamma)
dV/dt = (T-D)/m - g sin(gamma)
dm/dt = -cT T [1+beta(V-Vopt)^2]
```

主模型采用运动学风场：`W(h)` 只进入 `dx/dt`，不直接进入空速动力学。若扩展到动力学风切变模型，需要在 `dV/dt` 或更完整的航迹角动力学中加入 `W'(h)` 诱导项，并重新推导 PMP 条件。

升力和阻力：

```text
CL = 2 m g cos(gamma)/(rho(h) V^2 S)
CD = CD0 + k CL^2
D = 0.5 rho(h) V^2 S CD
```

边界条件：

```text
x(0)=0, h(0)=9500, V(0)=240, m(0)=72450
x(tf)=189781.310, h(tf)=10577.124, V(tf)=240
m(tf) free, tf free
```

目标函数：

```text
min J = m0 - m(tf)
```

等价于最大化 `m(tf)`。不得固定终端质量后再最小化油耗。

## 7. 必要条件与诊断

Hamilton 函数：

```text
H = lambda_x [V cos(gamma)+W(h)]
  + lambda_h V sin(gamma)
  + lambda_V [(T-D)/m - g sin(gamma)]
  - lambda_m cT T Phi(V)
```

其中 `Phi(V)=1+beta(V-Vopt)^2`。

必须推导并保存：

- 状态方程；
- 伴随方程 `dot(lambda)=-partial H/partial z`；
- `partial H/partial T=0` 或推力边界控制条件；
- `partial H/partial gamma=0` 或航迹角边界控制条件；
- 固定终端 `x,h,V` 和自由终端 `m` 的伴随横截条件；
- 自由终端时间条件 `H(tf)=0`；
- 状态约束和控制约束激活时的 KKT 条件。

正式求解后用 PMP 驻值残差、Hamiltonian 平坦性和边界乘子一致性做诊断，不把 PMP 作为第一版主求解器。简单的 `partial H/partial T=0`、`partial H/partial gamma=0` 只适用于无控制变化率约束或变化率约束不激活的区间；若加入严格的 `|dot T|`、`|dot gamma|`，需把 `T,gamma` 扩展为状态，新增控制 `u_T=dot T,u_gamma=dot gamma`。

## 8. 直接法设计

- 主方法：第一版数值实现采用航程域直接法，独立变量 `x in [0,Xf]`；时间域 PMP 推导保留为诊断理论。
- 航程域状态：`(h,V,m,t)`；控制：`(T,gamma)`。
- 航程域动力学：

```text
Vg = V cos(gamma) + W(h)
dh/dx = V sin(gamma)/Vg
dV/dx = [(T-D)/m - g sin(gamma)]/Vg
dm/dx = -cT T Phi(V)/Vg
dt/dx = 1/Vg
```

- 缺陷约束：对每个航程区间施加动力学积分约束；航程终点固定，不再把 `x` 作为状态或把 `tf` 作为优化变量。
- 初始网格：先用较少节点，例如 `N=31`，通过后再做 `N=61`、`N=121` 网格加密。
- 初值来源：配置风场可用 q2 固定路径剖面，`h_guess=h_ref(x)`、`V_guess=240`、`m_guess` 使用 q2 质量剖面、`gamma_guess=atan(dh_ref/dx)`、`T_guess` 由动力学反算；无风问题不能直接使用该剖面作为可行初值，需先构造满足质量下限的短航程初值或经优化可行性阶段寻找可行轨迹。
- 分阶段：先无风 `W=0`，再用无风解作为有风初值。
- 尺度化：NLP 内部使用无量纲变量，例如 `x/Xf`、`h/10000`、`V/240`、`m/72450`、`T/50000`、`t/800`、`gamma/0.05`，输出再还原为 SI 单位。
- 控制变化率：第一版不加入严格 `|dot T|`、`|dot gamma|` 约束，只使用控制上下界和小的相邻控制平滑正则；严格变化率约束留给扩展状态版本。
- 自由终端时间：除最小燃油主目标外，必须报告 `tf`，并做 `tf<=1.05 t_base`、`tf<=1.10 t_base` 或 `J_alpha=m0-m(tf)+alpha tf` 的运营约束对照。无风时间基准使用无风固定路径 `790.755 s`，有风时间基准使用配置风场固定路径 `721.753 s`。
- 线性推力油耗：`T_min=0` 会产生零推力零油耗的模型偏差。正式求解需至少做一种处理：设置 `T_idle>0`、加入基础油耗项，或明确声明零推力边界只是题面简化模型结果并做 `T_min` 敏感性。
- 11 km 大气层边界：若 `h_max` 允许超过 11000 m，需使用分层 ISA 的可微过渡或限制 `h_max<11000 m`；否则梯度型求解和 PMP 残差可能在层边界附近不稳定。
- 当前 Gate 1 已达到 `h=12000 m` 并穿越 11 km 层界，因此完整 collocation 前必须采用 `10950-11050 m` 的 `C1` 平滑大气过渡，或改用 `h_max<=10950 m` 的对流层内版本。默认 Gate 2 采用 `C1` 平滑过渡。
- review4 后，Gate 2 的平滑大气口径固定为：只构造 `C1` 温度曲线 `T_s(h)`，压力由 `dp_s/dh=-g p_s/(R T_s)` 积分得到，密度和声速再由 `rho_s=p_s/(R T_s)`、`a_s=sqrt(gamma R T_s)` 计算；不得分别对 `T,p,rho` 独立插值。脚本需报告静力平衡残差和相对精确分层 ISA 的最大偏差。
- 可行性目标采用词典序两阶段：第一阶段只最小化质量缺口 `s`；第二阶段固定 `s<=s_min+epsilon_s` 后再最小化控制平滑项。不得用 `s+epsilon R(T,gamma)` 的单一加权目标牺牲可行性。
- Gate 通过标准预先固定为：`s<=0.05 kg`、尺度化配点缺陷无穷范数 `<=1e-6`、终端高度误差 `<=0.1 m`、终端空速误差 `<=1e-3 m/s`、所有状态/控制约束无量纲违反 `<=1e-6`。词典序第二阶段的松弛容差固定为 `epsilon_s=1e-3 kg`，小于最终通过阈值。
- Gate 1 轨迹只能作为 Gate 2 warm start。由于 Gate 2 更换为 C1 平滑大气，需将 Gate 1 的 `(h,V,T,gamma)` 插值到新网格并用新大气重新投影质量和时间；不得把旧模型下的 `m,t` 序列当作新模型可行状态。
- 高度约束检查不能只放在主节点；Gate 2 至少应检查节点、配点中点以及最终重构网格上的 `h<=h_max`。

## 9. 灵敏度与不确定性

- 边界敏感性：高度、速度、马赫、推力、航迹角、控制变化率。
- 网格敏感性：`N=31/61/121`。
- 初值敏感性：q2 初值、平直路径初值、扰动初值。
- 风场敏感性：无风、用户确认风场、风场系数扰动。
- 风场审计：在可行高度区间内报告 `W(h)` 范围和高度边界是否激活，避免把风场边界驱动的贴边轨迹解释为普遍气动规律。
- 高度上界敏感性：完整 collocation Gate 必须比较 `h_max in {10950, 11500, 12000, 12500} m`，并报告 `s*(h_max)`、`m_f(h_max)`、`t_f(h_max)` 和活跃约束。Gate 1 高度上界已几乎激活，`h_max` 是首要敏感参数。

## 10. 计划产物

本轮仅计划，不生成正式最优产物。

| 产物 ID | 类型 | 内容 | 生成脚本 | 数据文件 |
|---|---|---|---|---|
| q3-D01 | document | 题意审计 | manual | `questions/q3/review.md` |
| q3-D02 | document | PMP 必要条件推导 | manual | `questions/q3/derivation.md` |
| q3-D03 | document | 直接法求解设计 | manual | `questions/q3/approach.md` |
| q3-T00 | table | 固定路径无风/有风可行性预检查 | `questions/q3/scripts/precheck.py` | `questions/q3/artifacts/tables/baseline_feasibility.csv` |
| q3-T01 | table | 无风可行性 Gate | `questions/q3/scripts/solve_feasibility_no_wind.py` | `questions/q3/artifacts/tables/no_wind_feasibility_gate.csv` |
| q3-T02 | table | 无风 collocation Gate dry-run | `questions/q3/scripts/solve_feasibility_collocation_no_wind.py --dry-run` | `questions/q3/artifacts/tables/no_wind_collocation_gate.csv` |
| q3-T03 | table | 无风 collocation warm start 轨迹 | `questions/q3/scripts/solve_feasibility_collocation_no_wind.py --dry-run` | `questions/q3/artifacts/tables/no_wind_collocation_trajectory.csv` |
| q3-T04 | table | 无风 `h_max` warm start 敏感性 | `questions/q3/scripts/solve_feasibility_collocation_no_wind.py --dry-run` | `questions/q3/artifacts/tables/no_wind_hmax_sensitivity.csv` |
| q3-T05 | table | 无风最优结果 | planned | planned |
| q3-T06 | table | 最优解验证表 | planned | planned |

下一阶段先生成完整 collocation 可行性 Gate，并同步完成 `h_max` 敏感性和 11 km 大气层平滑处理。只有当 `s*` 满足预设通过标准后，才生成 `q3-T05` 无风最优结果和 `q3-T06` 最优解验证表。

## 11. 备用方案与停止条件

- 若直接法不可行：先放宽控制变化率，再检查边界条件和 q2 初值是否满足动力学。
- 若有风求解失败：保留无风阶段结果，用无风解逐步 continuation 到有风系数。
- 若最优结果比 q2 基线更差：记录为求解失败或局部最优，不得写成有效最优结论。
- 本轮停止条件：完成文档，不写正式最优求解脚本。
