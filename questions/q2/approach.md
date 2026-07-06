# q2 解法方案

## 1. 题意解释

- 原题要求：建立巡航全过程总燃油消耗量沿飞行路径的数学模型，明确国际标准大气中温度、密度和声速随高度连续变化如何进入模型，并绘制油耗率沿路径分布；再选择一种温度偏差处理方式重新计算总油耗。
- 数学目标：固定 q1 等速策略的几何路径 `h_ref(x)` 与速度路径 `V_ref(x)=240 m/s`，在标准 ISA 与常温偏差非标准大气下重新计算 `CL(x)`、阻力、推力需求和路径积分油耗。
- 输入：题设气动/燃油参数、q1 等速参考路径、用户确认风场 `W(h)=20+3e-5(h-10000)^2`。
- 输出：共同可行航程剖面、总油耗汇总表、温差灵敏度表、验证表、沿路径油耗率图、大气参数路径图和温差灵敏度图。
- 评价指标：初始状态一致性、终点质量约束、固定航程误差、总油耗、单位距离油耗、油耗率路径分布、温度修正效应、时间积分与路径积分一致性。
- 歧义与采用解释：`tasks/task2.md` 当前为空，采用 `question.md` 中的问题 2 作为权威题面；为避免固定终止质量导致各场景油耗恒定，先确定所有温差场景均满足 `m>=62000 kg` 的共同可行航程，再比较同一航程下的终点质量和油耗。

## 2. 符号、单位和约束

| 符号 | 含义 | 单位 | 范围 / 约束 |
|---|---|---|---|
| `X_ref` | 共同可行参考航程 | m | `189781.310` |
| `J` | 固定航程总燃油消耗 | kg | `m0-m(tf)` |
| `h_ref(x)` | q1 等速几何路径 | m | 起点 `9500 m`，最大约 `10578 m` |
| `V_ref(x)` | q1 等速真空速路径 | m/s | `240` |
| `T(h)` | 大气温度 | K | ISA 或常偏差非标准大气 |
| `p(h)` | 大气压力 | Pa | 满足静力平衡 |
| `rho(h)` | 大气密度 | kg/m^3 | `p/(R T)` |
| `a(h)` | 声速 | m/s | `sqrt(gamma R T)` |
| `q_f(t)` | 燃油流率 | kg/s | 必须为正 |
| `q_x(x)` | 单位距离油耗 | kg/m | `q_f/(V+W(h))` |

## 3. 数据与预处理

- 数据来源：`question.md` 题设参数和 q1 产物 `artifacts/q1/data/constant_speed_profile.csv`。
- 质量问题：`tasks/task2.md` 为 0 字节，已在 q2 文档中记录并改用 `question.md` 问题 2。
- 缺失值：q1 参考剖面为脚本生成结果，不涉及观测缺失值填补。
- 单位与尺度：全程 SI 单位；温度偏差采用 `DeltaT in {-10,-5,-2,0,2,5,10} K`。
- 防止泄漏：本问为机理积分模型，不涉及预测训练。

## 4. 基线方案

- 方法：标准 ISA 下沿 q1 等速几何路径积分。
- 标准大气：对流层内 `T=T0-Lh`，`p=p0(T/T0)^{g/(RL)}`，`rho=p/(RT)`，`a=sqrt(gamma R T)`。
- 为什么适合作为基线：题目要求获得标准大气条件下总油耗，并显示连续温度、密度、声速项如何进入路径积分模型。
- 与上一版区别：不再把 q1 指数密度模型下的固定 `CL_ref` 直接带入 ISA 反算高度，而是固定 q1 的几何路径，在每种大气中重新计算 `CL(x)`。

## 5. 候选模型

| 模型 | 适配性 | 假设 | 优点 | 风险 | 是否采用 |
|---|---|---|---|---|---|
| 固定终止质量积分 | 不适合油耗比较 | 所有场景都停在 `m=62000 kg` | 满足终止质量 | 各场景总油耗恒定，无法比较温差影响 | rejected |
| q1 固定 `CL_ref` 反算高度 | 不足 | q1 指数大气下的 `CL_ref` 可直接用于 ISA | 代码简单 | 初始高度偏离 `9500 m`，轨迹越过 11 km | rejected |
| 各场景重算初始 `CL_ref(DeltaT)` | 可用 | 每个场景保持各自初始升力系数 | 初始高度一致 | 不同场景 `CL` 数值不同，仍会改变几何路径 | deferred |
| 固定 q1 几何路径并重算 `CL(x)` | 最适合 q2 | 各场景飞同一 `h_ref(x),V_ref(x)` | 初始状态一致、隔离大气影响、路径低于 11 km | 不是最优路径 | adopted |

## 6. 主模型

常温偏差大气在对流层内采用：

```text
T_delta(h)=T0+DeltaT-Lh
p_delta(h)=p0 [(T0+DeltaT-Lh)/(T0+DeltaT)]^{g/(RL)}
rho_delta(h)=p_delta(h)/(R T_delta(h))
a_delta(h)=sqrt(gamma R T_delta(h))
```

代码也实现了 11 km 以上的等温层压力连续公式；当前 q2 固定路径最高低于 11 km，因此实际计算均在对流层内。

沿 q1 等速路径：

```text
h=h_ref(x),  V=V_ref(x)=240 m/s
CL(x)=2m(x)g/[rho_delta(h_ref(x)) V^2 S]
CD(x)=CD0+k CL(x)^2
D(x)=0.5 rho_delta(h_ref(x)) V^2 S CD(x)
V_g(x)=V+W(h_ref(x))
```

考虑小航迹角爬升功率项，燃油流率为：

```text
q_f = cT [D + m g (dh/dt)/V] [1+beta(V-Vopt)^2]
dh/dt = (dh_ref/dx) V_g
dm/dt = -q_f
dx/dt = V_g
```

题目要求的路径域表达为：

```text
dt = dx / V_g(x)
J = ∫_0^{X_ref} q_f(x)/V_g(x) dx
dm/dx = -q_f(x)/(V+W(h_ref(x)))
q_x(x)=q_f(x)/V_g(x)
```

共同参考航程的确定方式：

```text
对每个 DeltaT 场景，沿 q1 路径积分到 m=62000 kg；
取这些终止航程的最小值作为 X_ref；
再让所有场景飞同一个 X_ref。
```

这样所有温差场景均满足终点质量不低于题设终止质量。

## 7. 温度、密度和声速的作用说明

- 温度与压力共同决定密度剖面，密度在固定几何路径上直接改变 `CL(x)`、诱导阻力和总阻力。
- 高度路径固定后，温差影响不再混入“重新选择高度轨迹”的因素，更适合解释大气参数场沿路径的作用。
- 当前等真空速模型中，燃油惩罚项为 `1+beta(V-Vopt)^2`，由于 `V=240 m/s` 固定，声速不直接改变该惩罚项。
- 声速用于计算马赫数诊断；若后续加入等马赫策略、波阻或马赫相关发动机模型，声速才会直接进入油耗方程。

## 8. 验证与诊断

- 初始状态：`h(0)=9500 m`、`V(0)=240 m/s`、`m(0)=72450 kg`。
- 固定航程误差 `<1 m`。
- 所有场景终点质量 `m(tf)>=62000 kg`。
- 路径高度低于 `11000 m`，大气层公式适用。
- ISA 与常偏差大气参数均为正。
- 静力平衡残差 `|dp/dh+rho g|/(rho g) < 1e-4`。
- `DeltaT=0` 收敛回 ISA。
- 时间积分、路径积分和最终质量亏损一致。
- 步长敏感性检查 `max_step_s` 加倍后总油耗变化 `<0.1 kg`。
- 正负温差响应方向相反。
- 小航迹角、推力正性和路径导数平滑性检查通过。

## 9. 灵敏度与不确定性

- 关键扰动：`DeltaT in {-10,-5,-2,0,2,5,10} K`。
- 稳健性指标：总油耗变化量、相对变化比例、单位距离油耗和终点质量。
- 忽略条件：本组计算中 `|DeltaT|<=10 K` 的总油耗相对变化均小于 `0.3%`，若论文精度要求为 `1%`，该常温偏差影响可近似忽略；若要求亚千分级精度，应纳入修正。

## 10. 计划产物

| 产物 ID | 类型 | 内容 | 生成脚本 | 数据文件 |
|---|---|---|---|---|
| q2-T01 | table | 各温差共同可行航程总油耗 | `questions/q2/scripts/pipeline.py` | `artifacts/q2/data/q2_fuel_summary.csv` |
| q2-T02 | table | q2 验证检查 | `questions/q2/scripts/validate.py` | `questions/q2/artifacts/tables/validation_summary.csv` |
| q2-T03 | table | 温差灵敏度汇总 | `questions/q2/scripts/pipeline.py` | `artifacts/q2/data/q2_temperature_sensitivity.csv` |
| q2-F01 | figure | 沿路径油耗率分布 | `questions/q2/scripts/visualize.py` | `questions/q2/artifacts/figure_data/fuel_rate_path.csv` |
| q2-F02 | figure | 大气参数沿路径分布 | `questions/q2/scripts/visualize.py` | `questions/q2/artifacts/figure_data/atmosphere_path.csv` |
| q2-F03 | figure | 温差灵敏度曲线 | `questions/q2/scripts/visualize.py` | `questions/q2/artifacts/figure_data/temperature_sensitivity.csv` |

## 11. 备用方案与停止条件

- 主模型失败时：停止并记录，不输出固定航程油耗结论。
- 终点质量约束失败时：缩短共同可行航程，不允许输出低于 `62000 kg` 的场景作为主结论。
- 数据不足处理：若用户补充真实非标准温度剖面，则作为新场景重新计算并更新证据链。
