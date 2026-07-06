# q2 解法方案

## 1. 题意解释

- 原题要求：建立巡航全过程总燃油消耗量沿飞行路径的数学模型，明确国际标准大气中温度、密度和声速随高度连续变化如何进入模型，并绘制油耗率沿路径分布；再选择一种温度偏差处理方式重新计算总油耗。
- 数学目标：以 q1 等速策略地面航程 `X_ref=200668.442 m` 为固定终止航程，计算标准 ISA 与常温偏差非标准大气下的 `J=m0-m(tf)`。
- 输入：题设气动/燃油参数、q1 等速参考航程、用户确认风场 `W(h)=20+3e-5(h-10000)^2`。
- 输出：固定航程剖面、总油耗汇总表、温差灵敏度表、验证表、沿路径油耗率图、大气参数路径图和温差灵敏度图。
- 评价指标：固定航程误差、总油耗、单位距离油耗、油耗率路径分布、温度修正导致的油耗变化、时间积分与路径积分一致性。
- 歧义与采用解释：`tasks/task2.md` 当前为空，采用 `question.md` 中的问题 2 作为权威题面；为避免固定终止质量导致总油耗恒为 `10450 kg`，按固定 q1 参考航程进行比较。

## 2. 符号、单位和约束

| 符号 | 含义 | 单位 | 范围 / 约束 |
|---|---|---|---|
| `X_ref` | q1 等速参考航程 | m | `200668.442` |
| `J` | 固定航程总燃油消耗 | kg | `m0-m(tf)` |
| `T(h)` | 大气温度 | K | ISA 或常偏差非标准大气 |
| `p(h)` | 大气压力 | Pa | 满足静力平衡 |
| `rho(h)` | 大气密度 | kg/m^3 | `p/(R T)` |
| `a(h)` | 声速 | m/s | `sqrt(gamma R T)` |
| `q_f(t)` | 燃油流率 | kg/s | 必须为正 |
| `q_x(x)` | 单位距离油耗 | kg/m | `q_f/(V+W(h))` |

## 3. 数据与预处理

- 数据来源：`question.md` 题设参数和 q1 产物 `artifacts/q1/data/strategy_comparison.csv`。
- 质量问题：`tasks/task2.md` 为 0 字节，已在 q2 文档中记录并改用 `question.md` 问题 2。
- 缺失值：无观测数据，不涉及缺失值填补。
- 单位与尺度：全程 SI 单位；温度偏差采用 `DeltaT in {-10,-5,-2,0,2,5,10} K`。
- 防止泄漏：本问为机理积分模型，不涉及预测训练。

## 4. 基线方案

- 方法：标准 ISA 下固定航程积分，沿用 q1 等速 `V=240 m/s` 和固定参考升力系数闭合。
- 标准大气：`T=T0-Lh`，`p=p0(T/T0)^{g/(RL)}`，`rho=p/(RT)`，`a=sqrt(gamma R T)`。
- 为什么适合作为基线：题目要求获得标准大气条件下总油耗，并显示连续温度、密度、声速项如何进入模型。

## 5. 候选模型

| 模型 | 适配性 | 假设 | 优点 | 风险 | 是否采用 |
|---|---|---|---|---|---|
| 固定终止质量积分 | 不适合 q2 油耗比较 | `m(tf)=62000 kg` | 与 q1 一致 | 温度修正后总油耗恒定，无法回答 q2 | rejected |
| 忽略温度偏差 | 可作基线 | 真实大气等同 ISA | 简单、可解释 | 无法分析温度修正影响 | baseline |
| 固定 ISA 压力的温度修正 | 不足 | `p=p_ISA`，只改 `T` | 实现简单 | 不满足静力平衡，已被 review 否决 | rejected |
| 静力平衡常温偏差修正 | 适合当前题意 | `T_delta=T0+DeltaT-Lh` 且 `dp/dh=-rho g` | 物理一致，可做灵敏度 | 仍是假设性常偏差 | adopted |

## 6. 主模型

常温偏差大气采用

```text
T_delta(h)=T0+DeltaT-Lh
p_delta(h)=p0 [(T0+DeltaT-Lh)/(T0+DeltaT)]^{g/(RL)}
rho_delta(h)=p_delta(h)/(R T_delta(h))
a_delta(h)=sqrt(gamma R T_delta(h))
```

固定真空速、固定 `CL_ref` 操作规律下，由升力平衡反算高度：

```text
0.5 rho(h) V^2 S CL_ref = m g
```

随后计算阻力、隐式爬升功率项和燃油流率：

```text
dm/dt = -q_f
dx/dt = V_g = V + W(h)
```

题目要求的路径域表达显式写为：

```text
dt = dx / V_g(x)
J = ∫_0^{X_ref} q_f(x)/V_g(x) dx
dm/dx = -q_f(x)/(V+W(h(x)))
q_x(x)=q_f(x)/V_g(x)
```

数值实现仍用时间域 ODE 并以 `x(t_f)=X_ref` 事件终止，同时输出 `q_x`、累计时间积分和累计路径积分，用于交叉验证。

## 7. 温度、密度和声速的作用说明

- 温度与压力共同决定密度剖面，进而改变为满足同一 `CL_ref,V` 所需的高度轨迹。
- 高度轨迹变化会改变爬升功率项、风速 `W(h)` 和固定航程所需时间。
- 当前等真空速模型中，燃油惩罚项为 `1+beta(V-Vopt)^2`，由于 `V=240 m/s` 固定，声速不直接改变该惩罚项。
- 声速用于计算马赫数诊断；若后续加入等马赫策略、波阻或马赫相关发动机模型，声速才会直接进入油耗方程。

## 8. 验证与诊断

- 固定航程误差 `<1 m`。
- ISA 与常偏差大气参数均为正。
- 静力平衡残差 `|dp/dh+rho g|/(rho g) < 1e-4`。
- `DeltaT=0` 收敛回 ISA。
- 时间积分、路径积分和最终质量亏损一致。
- 步长敏感性检查 `max_step_s` 加倍后总油耗变化 `<0.1 kg`。
- 正负温差响应方向相反。
- 小航迹角、推力正性和路径导数平滑性检查通过。

## 9. 灵敏度与不确定性

- 关键扰动：`DeltaT in {-10,-5,-2,0,2,5,10} K`。
- 稳健性指标：总油耗变化量、相对变化比例、单位距离油耗和飞行时间。
- 忽略条件：本组计算中 `|DeltaT|<=10 K` 的总油耗相对变化均小于 `0.4%`，若论文精度要求为 `1%`，常温偏差可近似忽略；若要求亚千分级精度，则需要纳入修正。

## 10. 计划产物

| 产物 ID | 类型 | 内容 | 生成脚本 | 数据文件 |
|---|---|---|---|---|
| q2-T01 | table | 各温差固定航程总油耗 | `questions/q2/scripts/pipeline.py` | `artifacts/q2/data/q2_fuel_summary.csv` |
| q2-T02 | table | q2 验证检查 | `questions/q2/scripts/validate.py` | `questions/q2/artifacts/tables/validation_summary.csv` |
| q2-T03 | table | 温差灵敏度汇总 | `questions/q2/scripts/pipeline.py` | `artifacts/q2/data/q2_temperature_sensitivity.csv` |
| q2-F01 | figure | 沿路径油耗率分布 | `questions/q2/scripts/visualize.py` | `questions/q2/artifacts/figure_data/fuel_rate_path.csv` |
| q2-F02 | figure | 大气参数沿路径分布 | `questions/q2/scripts/visualize.py` | `questions/q2/artifacts/figure_data/atmosphere_path.csv` |
| q2-F03 | figure | 温差灵敏度曲线 | `questions/q2/scripts/visualize.py` | `questions/q2/artifacts/figure_data/temperature_sensitivity.csv` |

## 11. 备用方案与停止条件

- 主模型失败时：停止并记录，不输出固定航程油耗结论。
- 计算超时处理：检查高度反解和 ODE 事件终止条件。
- 数据不足处理：若用户补充真实非标准温度剖面，则作为新场景重新计算并更新证据链。
