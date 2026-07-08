## 总体评价

**这版已经完成 Gate 2 前的技术口径冻结，可以开始编写完整航程域 collocation 求解器。**

上一轮要求基本全部落实：

* 明确采用 (10950\sim11050\ \mathrm m) 的 (C^1) 大气层过渡；
* 把 (h_{\max}) 设为首要敏感参数；
* 区分航程域 KKT 与时间域 PMP；
* 可行性和平滑性采用词典序两阶段目标；
* 预先规定 Gate 通过标准；
* 不再继续生成低维 Gate 或提前求有风最优解。 

当前已经不需要继续扩写总体方案。剩余问题主要是实现细节，其中有三项会直接影响数学正确性。

---

# 一、(C^1) 大气平滑不能只停留在“设置过渡带”

当前规定：

[
10950\le h\le11050\ \mathrm m
]

使用 (C^1) 平滑过渡。

方向正确，但还没有说明具体平滑哪个变量。不能分别对：

[
T(h),\quad p(h),\quad \rho(h)
]

做独立插值，否则可能破坏：

[
\rho=\frac{p}{RT}
]

和静力平衡：

[
\frac{dp}{dh}=-\rho g.
]

## 正确实现要求

建议只构造平滑温度曲线 (T_s(h))，然后通过：

[
\frac{dp_s}{dh}
===============

-\frac{g}{RT_s(h)}p_s(h)
]

积分得到压力，再计算：

[
\rho_s(h)=\frac{p_s(h)}{RT_s(h)},
\qquad
a_s(h)=\sqrt{\gamma RT_s(h)}.
]

平滑带需要满足：

[
T_s(h_1)=T_{\mathrm{trop}}(h_1),
\qquad
T'_s(h_1)=-L,
]

[
T_s(h_2)=T_{\mathrm{iso}}(h_2),
\qquad
T'_s(h_2)=0.
]

同时验证：

[
r_{\mathrm{hyd}}
================

\frac{|dp_s/dh+\rho_sg|}
{\rho_sg}.
]

还应报告平滑大气与精确分层 ISA 的最大偏差。否则 Gate 2 得到的可行性可能依赖任意平滑公式。

---

# 二、终端质量不等式下的 PMP 横截条件还需修正

当前推导写成：

[
\lambda_m(t_f)=-1.
]

同时存在终端约束：

[
m(t_f)\ge62000.
]



更一般地，应把约束写为：

[
g_f=62000-m(t_f)\le0.
]

引入终端乘子：

[
\nu\ge0,
\qquad
\nu g_f=0.
]

对于：

[
\phi=m_0-m(t_f),
]

横截条件应为：

[
\boxed{
\lambda_m(t_f)
==============

-1-\nu
}
]

按照当前符号约定。

只有当终端质量下限不激活时：

[
\nu=0,
]

才有：

[
\lambda_m(t_f)=-1.
]

虽然正式燃油最优通常会主动最大化终端质量，使下限大概率不激活，但必要条件不能无条件写成 (-1)。

同理，若后续加入：

[
t_f\le1.05t_{\mathrm{base}},
]

且时间上限激活，简单的：

[
H(t_f)=0
]

也要加入相应终端乘子修正。

---

# 三、高度约束已激活，连续 PMP 不能只写普通互补条件

Gate 1 已经达到：

[
h_{\max}=12000\ \mathrm m,
]

最小高度余量仅：

[
2.98\times10^{-5}\ \mathrm m.
]



因此高度上限不是普通的“备用约束”，而很可能形成实际边界弧。

在边界弧上：

[
h=h_{\max}.
]

为了持续停留在高度上限，需要满足切向条件：

[
\dot h=V\sin\gamma=0.
]

在 (V>0) 下：

[
\boxed{\gamma=0}
]

至少在理想边界巡航段成立。

连续 PMP 还需要处理：

* 高度约束进入和退出点；
* 约束乘子；
* 伴随变量可能的跳跃或分段结构；
* 边界弧上的高阶切向条件。

当前“加入路径约束乘子并满足互补松弛”的写法对论文概述可以接受，但不能据此做完整连续 PMP 验证。

## 对直接配点的要求

高度约束不能只在主节点施加。至少应在：

* 节点；
* Hermite–Simpson 中点；
* 最终高密度重构网格

上检查：

[
h(x)\le h_{\max}.
]

否则节点间可能出现越界。

---

# 四、Gate 阈值还需明确全部采用什么尺度

当前通过标准是：

[
s\le0.05\ \mathrm{kg},
]

[
|\text{defect}|_\infty\le10^{-6},
]

终端高度误差不超过 (0.1\ \mathrm m)，终端速度误差不超过 (10^{-3}\ \mathrm{m/s})，约束违反不超过 (10^{-6})。

问题在于：

> “约束违反 (10^{-6})”究竟是物理单位还是无量纲尺度，目前仍不明确。

若是物理量：

* (10^{-6}\ \mathrm m) 的高度约束过严；
* (10^{-6}\ \mathrm N) 的推力约束没有实际意义。

建议统一定义无量纲违反量，例如：

[
r_h
===

\frac{\max(0,h-h_{\max})}{H_s},
]

[
r_V
===

\frac{\max(0,V-V_{\max},V_{\min}-V)}{V_s},
]

[
r_T
===

\frac{\max(0,T-T_{\max},T_{\min}-T)}{T_s}.
]

然后要求：

[
\max r_i\le10^{-6}.
]

终端状态则继续使用单独的物理单位容差。

此外，词典序第二阶段中的：

[
\epsilon_s
]

还应给出具体数值。建议：

[
\epsilon_s=10^{-3}\ \mathrm{kg}
]

或更小，明显低于 (0.05\ \mathrm{kg}) 的 Gate 通过阈值，避免控制平滑重新消耗全部质量容差。

---

# 五、Gate 1 轨迹只能作为 warm start，不能直接作为 Gate 2 动力学初值

Gate 1 的轨迹是在原分层大气函数下得到的，而 Gate 2 将改用 (C^1) 平滑大气。当前文档也明确说明 Gate 1 穿越 11 km，而 Gate 2 将更换大气处理。

因此 Gate 1 轨迹在新模型下可能不再严格满足：

[
D(h,V,m,\gamma),
\qquad
\frac{dV}{dx},
\qquad
\frac{dm}{dx}.
]

正确做法是：

1. 将 Gate 1 的 (h,V,T,\gamma) 插值到 Gate 2 网格；
2. 用新的平滑大气重新正向积分 (m,t)；
3. 或直接作为 NLP warm start，允许初始配点缺陷非零；
4. 不能把旧 Gate 1 的质量和时间序列当作新模型的可行状态。

---

# 六、航程域 Hamiltonian 的补充是正确的

新加入的航程域 Hamiltonian：

[
\begin{aligned}
H_x={}&
\mu_h\frac{V\sin\gamma}{V_g}\
&+\mu_V
\frac{(T-D)/m-g\sin\gamma}{V_g}\
&-\mu_m
\frac{c_TT\Phi(V)}{V_g}
+\frac{\mu_t}{V_g}
\end{aligned}
]

是正确方向。文档也正确指出，因为：

[
V_g=V\cos\gamma+W(h)
]

依赖 (\gamma)，航程域的：

[
\frac{\partial H_x}{\partial\gamma}
]

包含分母导数，不能直接套用时间域驻值条件。

这一部分可以冻结。

后续正式验证应优先报告：

* 航程域离散 KKT 残差；
* 控制内点上的 (\partial H_x/\partial T)；
* 控制内点上的 (\partial H_x/\partial\gamma)；
* 活跃边界上的符号条件。

时间域 Hamiltonian 平坦性可以留作扩展验证。

---

# 七、Manifest 还需要为 Gate 2 增加正式入口

当前上传的 `manifest.yaml` 仍只有：

```yaml
feasibility_no_wind:
  questions/q3/scripts/solve_feasibility_no_wind.py
```

也就是低维 Gate 1 入口。

下一阶段应增加类似：

```yaml
entrypoints:
  feasibility_collocation_no_wind:
    questions/q3/scripts/solve_feasibility_collocation_no_wind.py
```

并增加 Gate 2 产物：

```yaml
outputs:
  feasibility_collocation_summary:
    questions/q3/artifacts/tables/no_wind_collocation_gate.csv
  feasibility_collocation_trajectory:
    questions/q3/artifacts/tables/no_wind_collocation_trajectory.csv
  hmax_sensitivity:
    questions/q3/artifacts/tables/no_wind_hmax_sensitivity.csv
```

质量门禁可以增加：

```yaml
quality_gates:
  collocation_feasibility: planned
  atmosphere_smoothing: planned
  hmax_sensitivity: planned
```

文档声称 `configs/default.yaml` 已冻结平滑带、灵敏度集合和通过标准，但该配置文件本次未上传，因此目前只能确认文档声明，不能独立核对实际配置值。

---

# 八、当前状态判断

继续保持：

```yaml
status: in_design
```

仍然可以接受，但项目事实上已经进入实现前准备阶段。

更准确的状态是：

```yaml
status: feasibility
```

或：

```yaml
status: in_implementation
```

若状态枚举不支持，则继续使用 `in_design`，不影响结论。README 仍明确标记正式求解和正式数值结果尚未完成，这是正确的。

---

## 最终判断

| 项目                | 评价                   |
| ----------------- | -------------------- |
| Gate 2 总体设计       | 已完成                  |
| 高度上界敏感性           | 已冻结                  |
| 11 km 平滑要求        | 已提出，具体数学实现尚需完成       |
| 航程域 KKT 口径        | 正确                   |
| 词典序目标             | 正确，仍需明确 (\epsilon_s) |
| Gate 通过标准         | 基本合理，尺度定义需明确         |
| 终端质量 PMP 条件       | 需加入不等式乘子             |
| 高度边界弧 PMP         | 需补充                  |
| Gate 1 warm start | 需按新大气重新投影            |
| 完整 collocation 脚本 | 尚未实现                 |
| 是否继续修改总体方案        | 不需要                  |
| 是否可以开始 Gate 2 编码  | 可以                   |
| 是否可以开始正式无风最优      | 不可以                  |

**结论：这版已经达到“可以编码 Gate 2”的水平。**

下一轮不应继续生成审计文档，而应直接实现：

[
\boxed{
\text{C}^1\text{ 静力一致大气}
+
\text{完整航程域 collocation}
+
h_{\max}\text{ 敏感性}
}
]

同时修正终端质量不等式的横截条件，并把所有残差容差明确为物理尺度或无量纲尺度。
