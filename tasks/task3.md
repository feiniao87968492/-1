你现在是本数学建模项目第三问的最优控制建模 Agent。

本轮只完成题意审计、优化问题定义、必要条件推导和数值求解方案设计。不得立即生成正式最优数值，不得伪造优化结果。

开始前依次阅读：

1. `AGENTS.md`
2. `question.md`
3. `questions/q1/approach.md`
4. `questions/q1/derivation.md`
5. `questions/q1/results.md`
6. `questions/q2/approach.md`
7. `questions/q2/results.md`
8. `questions/q2/evidence.md`
9. `artifacts/q1/data/constant_speed_profile.csv`
10. `artifacts/q2/data/q2_fuel_summary.csv`
11. `configs/default.yaml`

## 一、建立第三问文档

建立并填写：

* `questions/q3/README.md`
* `questions/q3/brief.md`
* `questions/q3/review.md`
* `questions/q3/approach.md`
* `questions/q3/derivation.md`
* `questions/q3/experiments.md`
* `questions/q3/evidence.md`
* `questions/q3/results.md`
* `questions/q3/manifest.yaml`

本轮将 `results.md` 标记为待优化，不写入最优数值。

## 二、题意审计

必须记录以下问题：

1. 若继续固定终止质量 `m(tf)=62000 kg`，总燃油目标将退化为常数。
2. 主优化问题应固定航程，并最大化终端质量。
3. 若终端高度和速度均自由，优化器可能通过降低终端机械能获得虚假省油结果。
4. 必须固定终端高度和速度，或固定终端能量高度。
5. 题面称高度和速度为控制变量，但正式动力学应将其作为状态轨迹。
6. 推荐物理控制量为推力 `T(t)` 和航迹角 `gamma(t)`。
7. 必须设置高度、速度、马赫数、推力和航迹角约束。
8. 若没有控制变化率约束，推力可能出现 bang-bang 或非物理跳变。
9. 无风最优解应作为有风问题的初始解。
10. 直接法用于主求解，PMP 用于必要条件和结果验证。

将审计结果写入 `questions/q3/review.md`。

## 三、比较工况

采用 q2 的共同鲁棒可行航程作为固定目标距离：

`Xf = 189781.310 m`

初始条件：

`x(0)=0`

`h(0)=9500 m`

`V(0)=240 m/s`

`m(0)=72450 kg`

终端条件：

`x(tf)=Xf`

终端高度和速度默认取 q1 等速参考路径在 `Xf` 处的值：

`h(tf)=h_ref(Xf)`

`V(tf)=240 m/s`

若采用终端能量约束替代，必须解释其与固定高度、速度的差异，并保留一个主方案，不能在代码中混用。

## 四、动力学

状态变量：

`z=(x,h,V,m)`

控制变量：

`u=(T,gamma)`

动力学：

`dx/dt = V cos(gamma) + W(h)`

`dh/dt = V sin(gamma)`

`dV/dt = (T-D)/m - g sin(gamma)`

`dm/dt = -cT*T*[1+beta(V-Vopt)^2]`

升力平衡：

`CL = 2 m g cos(gamma)/(rho(h) V^2 S)`

阻力：

`CD = CD0 + k CL^2`

`D = 0.5 rho(h) V^2 S CD`

标准大气、风场和气动函数必须复用公共模块，不得重新复制一套不一致公式。

## 五、目标函数

采用：

`min J = m0 - m(tf)`

等价于：

`max m(tf)`

同时保存并验证：

`m0-m(tf) = integral_0^tf cT*T*[1+beta(V-Vopt)^2] dt`

不得固定终端质量后再最小化油耗。

## 六、约束

所有具体边界必须放入 `configs/default.yaml`，不得散落在脚本中。

至少包括：

* `h_min <= h <= h_max`
* `V_min <= V <= V_max`
* `V/a(h) <= M_max`
* `T_min <= T <= T_max`
* `abs(gamma) <= gamma_max`
* `abs(dT/dt) <= T_rate_max`
* `abs(dgamma/dt) <= gamma_rate_max`
* `m >= 62000 kg`

若题面未给具体数值，必须在 `review.md` 中说明其为竞赛仿真假设，并设计边界敏感性分析。

## 七、必要条件

推导 Hamilton 函数：

`H = lambda_x*[V cos(gamma)+W(h)]`
`  + lambda_h*V sin(gamma)`
`  + lambda_V*[(T-D)/m-g sin(gamma)]`
`  - lambda_m*cT*T*Phi(V)`

其中：

`Phi(V)=1+beta(V-Vopt)^2`

推导并记录：

* 状态方程；
* 伴随方程；
* `dH/dT=0` 或边界控制条件；
* `dH/dgamma=0` 或边界控制条件；
* 终端伴随条件；
* 自由终端时间条件 `H(tf)=0`；
* 状态约束激活时的 KKT 条件。

不要求手工完全展开所有长导数，但必须给出可计算的符号结构，特别是：

* `dD/dh`
* `dD/dV`
* `dD/dm`
* `dD/dgamma`
* `dW/dh`

## 八、直接法设计

主求解方法采用直接配点或 Hermite-Simpson 转录。

时间归一化：

`tau=t/tf in [0,1]`

优化变量至少包括：

* 每个节点的 `x,h,V,m`
* 每个节点的 `T,gamma`
* 终端时间 `tf`

动力学作为缺陷约束。

第一版网格建议从较少节点开始，再进行网格加密，不得直接使用高密度网格掩盖建模问题。

使用 q2 固定路径作为初值：

* `h_guess=h_ref(x)`
* `V_guess=240`
* `m_guess` 使用 q2 质量剖面
* `T_guess` 由动力学反算
* `gamma_guess=arctan(dh_ref/dx)`

## 九、分阶段求解

### 阶段 A：无风

设置：

`W(h)=0`

求解无风最优轨迹，并验证：

* 动力学缺陷；
* 边界条件；
* 约束余量；
* 总燃油积分；
* 网格敏感性；
* Hamiltonian 或驻值残差；
* 最优结果是否优于 q2 基线。

### 阶段 B：有风

使用无风最优解作为初值，加入：

`W(h)=20+3e-5(h-10000)^2`

比较无风和有风：

* 高度轨迹；
* 速度轨迹；
* 推力；
* 航迹角；
* 总时间；
* 总油耗；
* 约束激活区间。

## 十、能量高度分析

定义：

`E=h+V^2/(2g)`

推导无风时：

`dE/dt=(T-D)V/(mg)`

说明航迹角项为何消失。

明确列出能量高度降维成立的条件：

* 无风或风与高度无关；
* 小航迹角；
* 目标和约束可由能量状态表示；
* 无独立高度/速度/马赫限制；
* 终端条件只约束总机械能。

说明有风时：

`dx/dt=V cos(gamma)+W(h)`

中的 `W(h)` 使单位航程油耗显式依赖高度，导致相同能量高度的不同 `h,V` 组合不再等价。

## 十一、验证计划

至少设计：

1. 初始条件检查；
2. 终端距离、高度和速度检查；
3. 动力学缺陷残差；
4. 总油耗积分与质量亏损一致；
5. 状态和控制边界检查；
6. 马赫数限制检查；
7. 推力和航迹角变化率检查；
8. 小航迹角检查；
9. 网格加密敏感性；
10. 不同初值重复求解；
11. 无风解与有风解目标值比较；
12. PMP 驻值或 Hamiltonian 诊断；
13. 基线策略必须是优化问题的可行解；
14. 最优结果不能比基线更差，除非求解失败并明确记录。

## 十二、停止条件

本轮完成文档后停止，不写正式求解脚本。

列出：

* 已确认的优化口径；
* 尚需人工确认的约束边界；
* 终端高度和速度数值；
* 计划采用的直接法实现；
* 无风初值来源；
* 可能导致不可行或局部最优的风险；
* 第二轮需要建立的脚本文件。
