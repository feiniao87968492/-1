## 总体评价

**这版已经把 Gate 2 dry-run 阶段的两个核心疑点解释清楚，内部逻辑基本闭环。**

尤其是：

* C1 大气确实进入了密度、阻力和速度动力学链路；
* 固定推力、固定 (V,\gamma) 时，质量方程本身不含密度，因此切换大气模型后 (dm/dx) 不变是模型结构所致；
* 静力平衡不再只用构造公式自检，而是增加了压力函数的独立有限差分检查；
* manifest 中区分了 warm-start 高度诊断与未来真正的优化后高度敏感性；
* 仍明确标记为 `in_implementation`，没有把 dry-run 包装成 Gate 2 已通过。

现在可以作出明确判断：

> **dry-run 审计已经足够，不应继续增加第七轮 readiness 文档；下一步必须实现非 dry-run collocation NLP。**

---

# 一、对 (m_f^B=m_f^C) 的解释是正确的

航程域质量方程为：

[
\frac{dm}{dx}
=============

-\frac{c_TT\Phi(V)}
{V\cos\gamma+W(h)}.
]

在无风情况下：

[
W=0.
]

若诊断点或 warm start 中保持：

[
T,\quad V,\quad\gamma
]

完全相同，则 (dm/dx) 不显含：

[
\rho,\quad D,\quad p,\quad a.
]

因此，尽管 C1 大气使：

[
\Delta\rho=-1.3607\times10^{-4}\ \mathrm{kg/m^3},
]

[
\Delta D=-2.843\ \mathrm N,
]

[
\Delta!\left(\frac{dV}{dx}\right)
=================================

1.806\times10^{-7}\ \mathrm{m^{-1}},
]

仍然有：

[
\Delta!\left(\frac{dm}{dx}\right)=0.
]

这在数学上没有矛盾。

所以此前 Gate 1 到 Gate 2 投影中，切换大气后终端质量不变，**不能再被认为是 C1 大气没有接入代码**。

---

# 二、当前耦合诊断还不是“端到端燃油影响”诊断

现有诊断固定：

[
T=50000\ \mathrm N.
]

它证明了：

[
\rho\rightarrow D\rightarrow dV/dx
]

的链路正常，但没有证明：

[
\rho\rightarrow D\rightarrow T_{\mathrm{required}}
\rightarrow dm/dx
]

这一完整燃油链路。

在动力学一致轨迹上，若给定目标速度梯度 (V_x)，所需推力应为：

[
T_{\mathrm{req}}
================

D
+
m\left[
g\sin\gamma
+
V_g\frac{dV}{dx}
\right].
]

因此不同大气模型会导致：

[
\Delta T_{\mathrm{req}}
=======================

\Delta D,
]

继而导致：

[
\Delta!\left(\frac{dm}{dx}\right)
=================================

-\frac{c_T\Phi(V)}
{V_g}
\Delta T_{\mathrm{req}}.
]

## 建议增加一个最终耦合单元测试

固定：

[
h,V,m,\gamma,\frac{dV}{dx},
]

分别计算：

[
T_{\mathrm{req,layer}},
\qquad
T_{\mathrm{req,C1}},
]

以及：

[
\left(\frac{dm}{dx}\right)*{\mathrm{layer}},
\qquad
\left(\frac{dm}{dx}\right)*{\mathrm{C1}}.
]

预期结果应是：

[
\Delta T_{\mathrm{req}}\ne0,
\qquad
\Delta(dm/dx)\ne0.
]

这项测试不是继续审计 dry-run 的必要门槛，但应在正式 NLP 前加入，以证明大气变化最终能够通过优化推力影响燃油。

---

# 三、有限差分静力残差是实质改进

目前报告：

[
r_{\mathrm{hyd,formula}}
========================

2.219\times10^{-16},
]

以及独立有限差分结果：

[
r_{\mathrm{hyd,FD,max}}
=======================

1.194\times10^{-8},
]

[
r_{\mathrm{hyd,FD,RMS}}
=======================

2.099\times10^{-9}.
]



这比只报告机器精度级构造残差可信得多。

不过还需要明确两点。

## 1. 残差是否无量纲

若定义为：

[
r_{\mathrm{hyd}}
================

\frac{|p_h+\rho g|}{\rho g},
]

则 (1.19\times10^{-8}) 是无量纲相对残差，表现很好。

若定义为：

[
|p_h+\rho g|,
]

则应给出单位，例如 (\mathrm{Pa/m})。

CSV 字段或说明中应明确残差定义。

## 2. 检查差分步长收敛

中心差分结果依赖步长 (\Delta h)。建议测试：

[
\Delta h\in{0.1,0.5,1,2,5}\ \mathrm m,
]

观察残差先按二阶精度下降，再受舍入误差影响。

否则单独一个 (1.19\times10^{-8}) 只能证明某个特定步长下表现良好。

---

# 四、正式 NLP 最重要的验证不是“配点缺陷等式残差”

梯形配点约束为：

[
z_{i+1}-z_i
-----------

\frac{\Delta x_i}{2}
\left[
f(z_i,u_i)+f(z_{i+1},u_{i+1})
\right]
=0.
]

求解器可以把这个代数残差压得非常小，但这只能证明：

> 离散 NLP 等式被满足。

它不自动证明离散轨迹接近连续 ODE 真解。

必须区分：

### 求解器可行性残差

[
r_{\mathrm{NLP}}
================

|\delta_{\mathrm{trap}}|_\infty.
]

### 离散化误差

将求解得到的 (T(x),\gamma(x)) 用高精度 ODE 求解器重新积分，比较：

[
r_{\mathrm{reint}}
==================

\max_x
\left|
z_{\mathrm{collocation}}(x)
---------------------------

z_{\mathrm{integrated}}(x)
\right|.
]

正式 Gate 2 至少应同时报告：

* `scaled_collocation_defect_inf`；
* `reintegration_state_error_inf`；
* `reintegration_terminal_mass_error_kg`；
* `reintegration_terminal_height_error_m`；
* `reintegration_terminal_speed_error_mps`。

再结合：

[
N=31,\ 61,\ 121
]

的网格收敛，才能判断轨迹是否真正可信。

---

# 五、梯形法下的“中点约束”需要明确定义

文档要求在节点、中点和重构网格检查：

[
h\le h_{\max}.
]

这是必要的，但当前使用的是梯形配点，而不是 Hermite–Simpson。

梯形法本身没有独立的中点状态决策变量，因此必须说明中点状态如何获得：

### 简单线性检查

[
z_{i+1/2}
=========

\frac{z_i+z_{i+1}}2.
]

这种方法容易实现，但不能发现非线性连续重构中的全部越界。

### 更可靠的 Hermite 重构

利用端点状态和端点导数构造区间多项式，再在多点检查状态约束。

建议正式 Gate 2 使用：

* 节点硬约束；
* 区间中点审计；
* 每个区间至少 5～10 个重构点的事后检查。

如果事后发现明显节点间越界，再升级到 Hermite–Simpson 或网格细化。

---

# 六、词典序第二阶段的松弛设置需要微调

目前设计为：

### 第一阶段

[
\min s.
]

### 第二阶段

[
s\le s_{\min}+10^{-3}\ \mathrm{kg},
]

然后最小化控制平滑项。

如果第一阶段得到：

[
s_{\min}=0,
]

第二阶段允许：

[
s\le0.001\ \mathrm{kg}.
]

这意味着第二阶段可能重新得到：

[
m_f=61999.999\ \mathrm{kg},
]

严格来说仍然违反：

[
m_f\ge62000\ \mathrm{kg}.
]

## 更合适的处理

若第一阶段满足：

[
s_{\min}\le0.05\ \mathrm{kg},
]

第二阶段直接移除松弛变量，并施加：

[
m_f\ge62000-\epsilon_{\mathrm{num}},
]

其中 (\epsilon_{\mathrm{num}}) 明确作为求解器数值容差。

或者若第一阶段确实得到 (s_{\min}=0)，直接固定：

[
s=0.
]

这样不会在控制平滑阶段重新牺牲硬质量约束。

---

# 七、Manifest 命名问题已基本解决

当前 manifest 已明确区分：

* `legacy_warm_start_hmax_diagnostic`；
* `warm_start_hmax_diagnostic`；
* `optimized_hmax_sensitivity`。

质量门也使用：

```yaml
optimized_hmax_sensitivity: planned
```

而不是模糊的 `hmax_sensitivity`。

这一处理已经足够清楚。旧兼容文件虽然仍存在，但不会再被主入口误认为正式优化结果。

---

# 八、证据链状态整体诚实，但前三项可以调整

证据链中的 Q3-C04 至 Q3-C09 对数值结论、dry-run 和诊断边界的描述较准确，尤其明确：

* Gate 1 不是全局可行性证明；
* dry-run 不执行优化；
* warm-start 高度表不能支持 (s^\star(h_{\max}))；
* C1 耦合诊断不支持正式最优结论。

但 Q3-C01、C02、C03 仍标为 `planned`：

* 优化目标退化分析已经完成；
* 固定终端机械状态的建模理由已经完成；
* 直接法和 PMP 诊断路线已经完成。

这些是理论或设计类主张，不需要等数值求解才能标记为支持。建议改成：

```text
supported_design
```

或至少：

```text
supported
```

并在“局限”中继续说明尚未进行正式数值验证。

---

# 九、目前仍无法独立复现数值

本次上传的是：

* 建模文档；
* 审计文档；
* manifest。

没有包含：

* `smooth_atmosphere.py`；
* `solve_feasibility_collocation_no_wind.py`；
* `configs/default.yaml`；
* 新增诊断 CSV；
* 测试代码。

因此当前可以确认的是：

* 文档内部逻辑正确；
* 关键数值之间没有明显矛盾；
* 对 (dm/dx) 为零差异的解释符合方程结构。

但不能独立重跑并确认这些数字。

所以 manifest 保持：

```yaml
reproducible: false
```

是正确的。

---

## 当前阶段的最终判断

| 项目                       | 评价                    |
| ------------------------ | --------------------- |
| C1 大气接入密度和阻力链路           | 已证明                   |
| C1 大气接入速度动力学             | 已证明                   |
| 固定推力下质量率不变               | 数学上正确                 |
| 端到端燃油耦合                  | 尚需 required-thrust 测试 |
| 独立静力残差                   | 已补充                   |
| 静力残差步长敏感性                | 尚未检查                  |
| 梯形离散口径                   | 已冻结                   |
| warm-start 高度诊断命名        | 已修复                   |
| 正式优化高度敏感性                | 尚未运行                  |
| 非 dry-run NLP            | 尚未实现                  |
| 项目状态 `in_implementation` | 准确                    |
| 是否继续增加 dry-run 审计        | 没有必要                  |
| 是否可以开始正式 Gate 2          | 可以                    |
| 是否可以开始燃油最优求解             | 不可以                   |

## 结论

**这版已经解决了上一轮最后一个实质性 dry-run 疑点。**

现在最重要的工作不再是增加 C10、C11 之类的新 readiness 证据，而是实际运行：

[
\boxed{
\min s
}
]

的完整梯形配点 NLP。

正式 Gate 2 的通过必须同时建立在：

[
s\le0.05\ \mathrm{kg},
]

[
|\delta_{\mathrm{trap}}|_\infty\le10^{-6},
]

[
\text{独立 ODE 重积分误差足够小},
]

以及：

[
N=31,\ 61,\ 121
]

结果稳定的基础上。
