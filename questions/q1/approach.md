# q1 解法方案

## 1. 题意解释

- 原题要求：建立巡航段高度、空速、水平距离和质量变化的耦合模型，并比较等速巡航爬升与等马赫数巡航爬升。
- 数学目标：在终止质量 `mf=62000 kg` 下，分别求解两种策略的时间序列，比较最终高度、总飞行时间、地面航程、爬升率和固定燃油消耗。
- 输入：`question.md`、`questions/q1/brief.md`、`tasks/overview.md`、`configs/default.yaml` 中的全局运行配置。
- 输出：两种策略的完整剖面、策略对比表、验证表、灵敏度表和五类论文级图表。
- 评价指标：升力平衡残差、能量方程残差、质量单调性、终止质量误差、步长敏感性、无风/有风对比、极端状态合理性。
- 歧义与采用解释：采用 `questions/q1/review.md` 已确认口径。飞行状态解释为小航迹角准稳态巡航爬升；`h,V` 是轨迹决策变量，物理控制量为 `T,gamma`；风场使用用户确认公式 `W(h)=20+3e-5(h-10000)^2`。

## 2. 符号、单位和约束

| 符号 | 含义 | 单位 | 范围 / 约束 |
|---|---|---|---|
| `t` | 飞行时间 | s | `t>=0` |
| `x(t)` | 水平地面距离 | m | 单调增加 |
| `h(t)` | 高度 | m | 由升力平衡与策略闭合决定 |
| `V(t)` | 真空速 | m/s | 等速策略固定为 `V0`，等马赫策略为 `M0 a(h)` |
| `m(t)` | 飞机质量 | kg | 从 `72450` 单调下降到 `62000` |
| `T(t)` | 推力 | N | 由能量方程反算，必须为正 |
| `D(t)` | 阻力 | N | 抛物线阻力极曲线，必须为正 |
| `rho(h)` | 空气密度 | kg/m^3 | 指数大气，必须为正 |
| `a(h)` | 声速 | m/s | 标准大气温度模型，必须为正 |
| `W(h)` | 沿航向风速 | m/s | 正值为顺风，主公式 `20+3e-5(h-10000)^2` |

## 3. 数据与预处理

- 数据来源：题面参数和用户确认口径，无外部数据。
- 质量问题：OCR 附表存在识别错误；风场口径以用户确认和 OCR 中的 `0.00003` 为准。
- 缺失值：无表格型观测数据，不涉及缺失值填补。
- 异常值：题面/overview 的风场系数差异单独登记，最终审计时说明。
- 单位与尺度：全部使用 SI 单位；`beta` 单位为 `s^2/m^2`，使速度惩罚项无量纲。
- 防止泄漏：本问为机理仿真，不涉及预测训练/测试划分。

## 4. 基线方案

- 方法：等真空速巡航爬升，`V(t)=V0`，并保持参考升力系数 `CL=CL_ref`。
- 为什么适合作为基线：题面要求比较等速策略；该策略可解析给出 `h=h0-Hrho ln(m/m0)`，可解释性强。
- 预期指标：终止质量固定，因此总油耗为 `10450 kg`；主要比较时间、航程、最终高度和爬升率分布。

## 5. 候选模型

| 模型 | 适配性 | 假设 | 优点 | 风险 | 是否采用 |
|---|---|---|---|---|---|
| 严格水平飞行 `dh/dt=0` | 不适配 | 无爬升 | 简单 | 与巡航爬升矛盾 | rejected |
| `T=D` 等推阻平衡模型 | 仅适合定高等速 | 忽略势能/动能变化 | 公式短 | 无法解释爬升能量来源 | rejected |
| 小角度准稳态能量模型 | 适配 q1 | `L≈mg`，`T=D+m dV/dt+mg dh/(Vdt)` | 可解释、可验证 | 依赖闭合条件 | adopted |

## 6. 主模型

- 数学定义：
  - `dx/dt = V + W(h)`；
  - `L = 0.5 rho V^2 S CL ≈ mg`；
  - `CD = CD0 + k CL^2`；
  - `D = 0.5 rho V^2 S CD`；
  - `T = D + m dV/dt + mg/V dh/dt`；
  - `dm/dt = -cT T [1 + beta (V - Vopt)^2]`。
- 闭合条件：两种策略均保持参考升力系数 `CL_ref=CL(h0,V0,m0)`。这是为闭合等速/等马赫巡航爬升轨迹而加入的操作假设，表示飞机通过连续调整迎角维持同一参考升力系数，不是由升力平衡自动推出的唯一结果。
- 参考值依据：按题设初始状态计算 `CL_ref=0.658914`，最大升阻比对应 `sqrt(CD0/k)=0.699206`，二者数量级接近，因此该闭合条件可视为接近高升阻比巡航爬升状态的可解释基线。
- 目标函数 / 损失：q1 不求优化最小值，目标是比较两种策略在固定终止质量下的过程指标。
- 约束：质量单调下降、密度/声速/推力/阻力为正、终止质量达到 `62000 kg`。
- 参数来源：题面参数、用户风场口径、标准大气常数、`configs/default.yaml` 数值容差。
- 求解算法：将 `h,V` 表示为 `m` 的函数，解出隐式质量 ODE 后用 `scipy.solve_ivp` 积分。
- 复杂度：一维 ODE，步长受 `max_step_s` 限制，计算量低。

## 7. 验证与诊断

- 基线比较：等速策略作为基线，等马赫策略与其比较。
- 主验证方法：单位/参数范围检查、初始条件、质量单调性、升力相对残差、能量相对残差、报告指标步长敏感性、无风/有风对比、极端高度/速度检查。
- 通过标准：升力和能量残差使用无量纲相对残差，阈值为 `1e-6`；报告指标步长敏感性检查 `final_time_s`、`final_distance_m` 和 `mean_climb_rate_mps`；敏感性结果无非物理状态。
- 失败案例：若题面原式风场或参数改动导致地速/推力异常，将记录为风险而不静默继续。

## 8. 灵敏度与不确定性

- 关键参数：积分最大步长、风场开关、`cT` 数量级、`beta` 扰动。
- 扰动范围：`beta` 扰动读取 `configs/default.yaml` 的 `validation.sensitivity_relative_changes=[-20%, -10%, +10%, +20%]`；另比较 `cT=2.8e-5`。
- 稳健性指标：最终时间、航程、最终高度、平均爬升率、最大残差。
- 极端场景：高度 `0-16000 m`、速度 `180-280 m/s` 下检查密度、声速、阻力和升力系数为物理值。

## 9. 计划产物

| 产物 ID | 类型 | 内容 | 生成脚本 | 数据文件 |
|---|---|---|---|---|
| q1-T01 | table | 两策略指标对比 | `questions/q1/scripts/pipeline.py` | `artifacts/q1/data/strategy_comparison.csv` |
| q1-T02 | table | 验证检查结果 | `questions/q1/scripts/validate.py` | `questions/q1/artifacts/tables/validation_summary.csv` |
| q1-T03 | table | 灵敏度结果 | `questions/q1/scripts/validate.py` | `questions/q1/artifacts/tables/sensitivity_summary.csv` |
| q1-F01 | figure | 高度-时间曲线 | `questions/q1/scripts/visualize.py` | `questions/q1/artifacts/figure_data/height_time.csv` |
| q1-F02 | figure | 质量-时间曲线 | `questions/q1/scripts/visualize.py` | `questions/q1/artifacts/figure_data/mass_time.csv` |
| q1-F03 | figure | 爬升率-时间曲线 | `questions/q1/scripts/visualize.py` | `questions/q1/artifacts/figure_data/climb_rate_time.csv` |
| q1-F04 | figure | 高度-距离曲线 | `questions/q1/scripts/visualize.py` | `questions/q1/artifacts/figure_data/height_distance.csv` |
| q1-F05 | figure | 两策略指标对比 | `questions/q1/scripts/visualize.py` | `questions/q1/artifacts/figure_data/strategy_metrics.csv` |

## 10. 备用方案与停止条件

- 主模型失败时：停止并记录失败，不输出伪结果；检查隐式质量方程分母、推力正性和声速模型。
- 计算超时处理：本问为一维 ODE，若超时说明模型异常，应降低输出频率或检查求解器设置。
- 数据不足处理：无外部数据；如需改动题面参数，必须写入决策记录。
