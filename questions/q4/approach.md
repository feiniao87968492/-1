# q4 解法方案

## 1. 题意解释

- 原题要求：在前三问基础上形成完整巡航策略综合数值模型，输出等速巡航爬升剖面、考虑风场的最优高度-速度轨迹、与等速策略的油耗和航程对比、`beta` 灵敏度，以及至少两个模型扩展方向。
- 数学目标：在统一飞机参数、风场和飞行包线下，比较基线巡航策略与有风局部优化策略的燃油效率和航程表现。
- 输入：题面参数、q1 等速路径、q2 共同可行航程、q3 无风最终优化轨迹，以及 q4 pipeline 生成的有风局部射击轨迹。
- 输出：基线表、局部优化轨迹表、策略对比表、`beta` 灵敏度表、扩展框架表、论文级剖面图和对比图。
- 评价指标：总燃油 `J=m0-m(tf)`、终端质量、总时间、终端高度/速度误差、固定航程油耗节省比例、固定燃油航程变化、约束违反、重积分误差和多初值一致性。
- 歧义与采用解释：题面同时要求“燃油节省比例”和“航程变化”。本轮采用双口径：主口径为固定 q2 共同可行航程 `Xf=189781.310 m` 比较油耗节省；补充口径为固定燃油或终止质量比较可达航程变化。若后续只允许单一口径，应优先保留固定航程油耗节省，因为它与 q3 最优控制定义一致。

## 2. 符号、单位和约束

| 符号 | 含义 | 单位 | 范围 / 约束 |
|---|---|---|---|
| `x` | 地面航程 | m | `0 <= x <= Xf` |
| `h` | 飞行高度 | m | 见 `configs/default.yaml` 中 q3 边界 |
| `V` | 真空速 | m/s | 见 `configs/default.yaml` 中 q3 边界 |
| `m` | 飞机质量 | kg | `m >= 62000` |
| `T` | 推力 | N | `0 <= T <= 90000` |
| `gamma` | 航迹角 | rad | `|gamma| <= 0.05236` |
| `W(h)` | 顺风风速 | m/s | `20+3e-5(h-10000)^2` |
| `beta` | 速度偏离惩罚系数 | s^2/m^2 | 标称 `0.003`，按配置扰动 |
| `J` | 总燃油消耗 | kg | `J=m0-m(tf)` |

## 3. 数据与预处理

- 数据来源：题面参数来自 `question.md`；q1/q2/q3 结果来自各小问已经登记的产物。
- 质量问题：q4 有风轨迹已由 `questions/q4/scripts/pipeline.py` 以 q3 无风轨迹 warm start 生成；该结果是低维控制结点的局部射击解，不支持全局最优表述。`beta` 灵敏度为逐场景重求解，但非标称场景未取得 SLSQP 成功终止标志，只支持局部可行敏感性。
- 缺失值：q4 当前无新原始数据；若上游 CSV 缺列或空表，pipeline 必须失败而不是生成占位结果。
- 异常值：检查高度、速度、质量、推力、马赫数、航迹角、地速分母和燃油率为正。
- 单位与尺度：沿用 SI 单位；风场正方向按 q1/q2 口径作为顺风项进入地速。
- 防止泄漏：`beta` 灵敏度必须对每个扰动重新求解，不得只在标称轨迹上后验重算油耗。

## 4. 基线方案

- 方法：复用 q1 等速巡航爬升剖面作为固定燃油基线；复用 q2 共同可行航程上的等速固定路径油耗作为固定航程基线。
- 为什么适合作为基线：q1/q2 已通过验证并形成证据链；等速策略是题面要求的传统策略，也是 q4 对比对象。
- 预期指标：终端高度、总时间、航程、燃油、终端质量、质量/燃油恒等式残差。

## 5. 候选模型

| 模型 | 适配性 | 假设 | 优点 | 风险 | 是否采用 |
|---|---|---|---|---|---|
| q3 reduced-control shooting 扩展到有风 | 高 | 控制结点分段线性，状态由航程域 ODE 连续积分 | 已在 q3 无风最终优化通过验收，易做 continuation | 有风局部最优和初值敏感 | 主方案 |
| 航程域全变量 collocation | 中 | 网格状态和控制同时优化 | 约束表达完整，适合 KKT 诊断 | SLSQP 已在 q3 全量 NLP 中超时，需稀疏求解器 | 交叉验证 |
| 固定 q1 路径后验重算 | 低 | 不优化轨迹，只比较油耗 | 快速生成诊断和 sanity check | 不能代表最优策略 | 仅作基线 |

## 6. 主模型

采用航程域点质量模型。令地速

```text
Vg = V cos(gamma) + W(h)
```

时间域动力学为

```text
dx/dt = Vg
dh/dt = V sin(gamma)
dV/dt = (T-D)/m - g sin(gamma)
dm/dt = -cT T [1 + beta (V-Vopt)^2]
```

航程域求解时除以 `Vg`，并增加 `dt/dx=1/Vg`。阻力、升力、密度、声速和马赫数沿用 q2/q3 的大气与气动实现。主目标为固定 `Xf=189781.310 m` 下最小化 `J=m0-m(tf)`，终端高度和速度沿用 q3 口径。补充目标为固定燃油或终止质量下估计可达航程，用于报告“航程变化”。本轮采用局部重优化航程网格和线性插值/下界估计，不写成严格全局最大航程。

- 目标函数 / 损失：主目标 `min J`；补充目标以多目标航程试验近似 `max X(tf)`。
- 约束：高度、速度、马赫、推力、航迹角、终端高度、终端速度、质量下限、燃油恒等式和连续重积分误差。
- 参数来源：题面给定、`configs/default.yaml`、q1/q2/q3 已登记结果。
- 求解算法：从 q3 无风最终轨迹初始化，使用有风航程域 ODE 和分段线性推力/航迹角控制结点做 SLSQP 局部优化；后续 `beta` 扰动必须逐场景重新求解。
- 复杂度：随控制结点数、`beta` 场景数和多初值数量近似线性增长；全量稀疏 NLP 作为后续增强。

## 7. 验证与诊断

- 基线比较：q4 pipeline 必须复现 q1/q2 关键基线数值，误差超过容差则停止。
- 主验证方法：独立 ODE 重积分、终端高度/速度误差、燃油恒等式、连续路径约束、目标网格/控制结点收敛、多初值一致性和风场开关回归。
- 通过标准：沿用 q3-T08 的重积分和约束门槛；q4-T02 当前终端高度误差 `6.31e-7 m`、速度误差 `1.51e-8 m/s`、最大尺度化约束违反 `0`、燃油恒等式残差 `0.0316 kg`，验证状态为 `passed`。q4-T04 每个 `beta` 场景均保留求解器消息和验证状态。
- 失败案例：有风 continuation 未收敛、固定燃油航程最大化未通过终端质量约束、`beta` 扰动结果出现局部最优跳变。

## 8. 灵敏度与不确定性

- 关键参数：`beta`。
- 扰动范围：默认使用 `configs/default.yaml` 的 `[-20%, -10%, +10%, +20%]`，并保留标称值。
- 稳健性指标：最优燃油、最优航程、终端时间、最大高度、平均速度、近零推力比例、活跃约束比例。
- 极端场景：若 `beta` 扰动导致求解失败，应保留失败行并记录失败原因，不得只报告成功场景。

## 9. 计划产物

| 产物 ID | 类型 | 内容 | 生成脚本 | 数据文件 |
|---|---|---|---|---|
| q4-T01 | table | 等速基线复现与固定航程基线（当前并入 q4-T03 baseline 行） | `scripts/pipeline.py` | `questions/q4/artifacts/tables/strategy_comparison.csv` |
| q4-T02 | table | 有风局部优化轨迹主结果 | `scripts/pipeline.py` | `questions/q4/artifacts/tables/wind_optimal_results.csv` |
| q4-T03 | table | 等速与局部优化策略对比 | `scripts/pipeline.py` | `questions/q4/artifacts/tables/strategy_comparison.csv` |
| q4-T04 | table | `beta` 重求解灵敏度 | `scripts/pipeline.py` | `questions/q4/artifacts/tables/beta_sensitivity.csv` |
| q4-T05 | table | 扩展框架与可实现接口 | `scripts/pipeline.py` | `questions/q4/artifacts/tables/extension_frameworks.csv` |
| q4-T06 | table | 固定燃油局部航程估计 | `scripts/pipeline.py` | `questions/q4/artifacts/tables/fixed_fuel_range.csv` |
| q4-F01 | figure | 高度-航程剖面对比 | `scripts/visualize.py` | `questions/q4/artifacts/figure_data/height_range_comparison.csv` |
| q4-F02 | figure | 速度/质量/推力剖面对比 | `scripts/visualize.py` | `questions/q4/artifacts/figure_data/profile_comparison.csv` |
| q4-F03 | figure | `beta` 灵敏度响应 | `scripts/visualize.py` | `questions/q4/artifacts/figure_data/beta_sensitivity.csv` |

## 10. 备用方案与停止条件

- 主模型失败时：保留 q4-T03 的基线行和失败诊断，不输出油耗节省结论；回退到 q4 有风 reduced-control shooting 子任务。
- 计算超时处理：先减少控制结点生成诊断表，再用更高结点确认；不得把低结点失败或未验证结果写成 supported。
- 数据不足处理：若 q3 无风 warm start 或 q1/q2 基线缺失，q4 pipeline 必须失败；不得生成占位油耗节省结论。
