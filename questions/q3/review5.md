## 总体评价

**这版已经从“Gate 2 设计完成”推进到了“Gate 2 基础设施可运行”。**

本轮新增内容是实质性的：

* C1 平滑大气已确定为“平滑温度—静力积分压力—状态方程计算密度”的一致方案；
* Gate 1 轨迹不再直接沿用旧的 (m,t)，而是在新大气下重新投影；
* 已建立 collocation dry-run 入口和三类输出；
* 终端质量不等式的 PMP 横截条件、高度边界弧条件已经修正；
* 残差尺度、松弛容差和 manifest 入口均已补齐。

因此现在可以开始真正实现并运行 Gate 2 NLP。

但需要明确：

> **当前通过的是 readiness/dry-run，不是 collocation 可行性 Gate。**

---

# 一、dry-run 的结果符合预期，但距离 Gate 通过仍有明显差距

当前 dry-run 得到：

[
m_f=61985.803\ \mathrm{kg},
]

[
s=14.197\ \mathrm{kg},
]

[
t_f=802.859\ \mathrm s,
]

尺度化配点缺陷：

[
|\delta_{\mathrm{col}}|_\infty
==============================

6.20\times10^{-5}.
]



而预设 Gate 标准是：

[
s\le0.05\ \mathrm{kg},
]

[
|\delta_{\mathrm{col}}|_\infty
\le10^{-6}.
]

因此当前：

* 质量缺口约为通过阈值的 (284) 倍；
* 配点缺陷约为通过阈值的 (62) 倍。

这并不表示实现失败，因为 dry-run 根本没有执行优化。它只说明：

1. warm start 可以成功投影；
2. 新大气模型能够运行；
3. 配点诊断链能够生成；
4. 初始点距离可行域不算特别远。

当前状态 `dry_run_not_optimized` 是准确的。

---

# 二、Gate 1 到 dry-run 的 3.983 kg 差异需要拆分来源

Gate 1 终点质量为：

[
61989.786\ \mathrm{kg},
]

dry-run 投影后为：

[
61985.803\ \mathrm{kg}.
]

二者差值：

[
61989.786-61985.803
===================

3.983\ \mathrm{kg}.
]

目前这部分差异混合了至少三种来源：

* 分层 ISA 改成 C1 平滑大气；
* Gate 1 轨迹插值到新节点；
* 重新推进 (m,t) 时使用的积分离散误差。

建议增加一个投影审计表，依次计算：

| 方案 | 大气        | 控制轨迹      | 积分网格      |
| -- | --------- | --------- | --------- |
| A  | 原分层 ISA   | 原 Gate 1  | 原网格       |
| B  | 原分层 ISA   | 插值 Gate 1 | Gate 2 网格 |
| C  | C1 平滑 ISA | 插值 Gate 1 | Gate 2 网格 |

这样可分解：

[
\Delta m_{\mathrm{interp}}
==========================

m_A-m_B,
]

[
\Delta m_{\mathrm{atmos}}
=========================

m_B-m_C.
]

否则暂时无法判断这 (3.983\ \mathrm{kg}) 主要来自大气修正还是网格投影。

---

# 三、C1 大气的设计方向正确，但证据还不完整

当前方案明确要求：

[
T_s(h)\in C^1,
]

压力通过：

[
\frac{dp_s}{dh}
===============

-\frac{g}{RT_s(h)}p_s(h)
]

积分，并由：

[
\rho_s=\frac{p_s}{RT_s},
\qquad
a_s=\sqrt{\gamma RT_s}
]

计算其余状态。

这是正确的处理方向。

当前已报告相对于精确分层 ISA 的最大绝对偏差：

[
\Delta T_{\max}=0.08125\ \mathrm K,
]

[
\Delta p_{\max}=0.044253\ \mathrm{Pa},
]

[
\Delta\rho_{\max}
=================

1.36\times10^{-4}\ \mathrm{kg/m^3}.
]



但还应把以下诊断直接放入结果表，而不能只由测试脚本隐含验证：

### 1. 端点连续性

在 (h_1=10950\ \mathrm m) 和 (h_2=11050\ \mathrm m) 报告：

[
|T_s-T_{\mathrm{layer}}|,
\qquad
|T_s'-T_{\mathrm{layer}}'|,
]

[
|p_s^- -p_s^+|,
\qquad
|\rho_s^- -\rho_s^+|.
]

### 2. 静力平衡残差

[
r_{\mathrm{hyd}}
================

\max_h
\frac{
\left|
dp_s/dh+\rho_sg
\right|
}{
\rho_sg
}.
]

### 3. 正值和单调性

至少检查：

[
T_s>0,\quad p_s>0,\quad\rho_s>0,
]

以及：

[
\frac{dp_s}{dh}<0.
]

当前文档说脚本会报告静力平衡残差，但 `results.md` 尚未实际给出数值，因此 `atmosphere_smoothing` 继续标为 `planned` 是合理的。

---

# 四、当前所谓 (h_{\max}) sensitivity 仍只是 warm-start 诊断

manifest 已生成：

```text
no_wind_hmax_sensitivity.csv
```

但 dry-run 没有针对每个 (h_{\max}) 重新最小化质量缺口。

因此这个表目前只能表示：

> 同一条 warm start 在不同高度上限下的裁剪、投影或初始违反情况。

它不能表示：

[
s^\star(h_{\max}).
]

正式结果应区分两个名称：

```text
warm_start_hmax_diagnostic.csv
```

和：

```text
optimized_hmax_sensitivity.csv
```

只有后者才能支持：

[
h_{\max}
\longmapsto
s^\star(h_{\max}).
]

当前证据链也正确地把 C06 定义为下一阶段门槛，而不是已经完成的数值结论。

---

# 五、需要正式冻结 collocation 离散公式

目前文档中：

* 时间域示例给出了梯形缺陷；
* 总体方案提到 Hermite–Simpson；
* Gate 2 又要求检查节点和配点中点。

但还没有明确正式 Gate 2 究竟采用：

1. 梯形配点；
2. Hermite–Simpson；
3. 其他中点配置。

这个选择会直接影响：

* 优化变量数量；
* 中点状态的定义；
* 配点缺陷计算；
* (10^{-6}) 阈值的含义；
* 乘子和 KKT 诊断。

## 推荐固定为 Hermite–Simpson

对区间 ([x_i,x_{i+1}])，先计算中点状态：

[
z_{i+\frac12}
=============

\frac{z_i+z_{i+1}}2
+
\frac{\Delta x_i}{8}
\left(f_i-f_{i+1}\right),
]

然后施加：

[
z_{i+1}-z_i
-----------

\frac{\Delta x_i}{6}
\left(
f_i+4f_{i+\frac12}+f_{i+1}
\right)
=0.
]

并在：

* 左节点；
* 中点；
* 右节点

同时检查状态和控制约束。

如果第一版实际准备采用梯形法，则应删掉“配点中点约束”的模糊表述，并把高密度重构检查作为独立验证。

---

# 六、终端质量 PMP 条件已经修正正确

现在文档写成：

[
g_f=62000-m(t_f)\le0,
]

[
\nu\ge0,
\qquad
\nu g_f=0,
]

[
\lambda_m(t_f)=-1-\nu.
]



按照当前目标函数和约束符号，这是正确的。

文档也正确说明：

* 只有约束不激活时才有 (\lambda_m(t_f)=-1)；
* 若终端时间上限激活，不能继续直接使用 (H(t_f)=0)；
* 高度边界弧上需要 (\dot h=0)，进而在 (V>0) 时有 (\gamma=0)。

这一部分可以冻结，不需要继续扩写。

---

# 七、dry-run 阶段不需要做完整 KKT 诊断

当前还没有运行 NLP，也就没有真实的：

* 缺陷约束乘子；
* 边界约束乘子；
* 控制驻值乘子；
* 终端不等式乘子。

所以此时不应尝试伪造：

[
\frac{\partial H_x}{\partial T},
\qquad
\frac{\partial H_x}{\partial\gamma}
]

的最优性残差。

dry-run 只需要报告：

* 初始 collocation defect；
* 初始端点误差；
* 初始路径约束违反；
* warm-start 质量缺口；
* 数值尺度范围。

等实际 NLP 求解完成后，再从求解器提取离散乘子，进行航程域 KKT 诊断。文档已经正确区分航程域乘子和时间域伴随变量。

---

# 八、Manifest 与 README 现在基本一致

Manifest 已包含：

```yaml
feasibility_collocation_no_wind
```

入口，以及：

* collocation summary；
* collocation trajectory；
* (h_{\max}) sensitivity。

质量门禁也保持：

```yaml
collocation_feasibility: planned
atmosphere_smoothing: planned
hmax_sensitivity: planned
```

没有因为 dry-run 成功就提前标记完成，这一点正确。

README 也明确区分：

* Gate 1；
* Gate 2 dry-run；
* 正式求解脚本尚未完成。

不过 `status: in_design` 已略显保守。当前更接近：

```yaml
status: in_implementation
```

但这只是项目管理命名问题，不影响模型可信度。

---

# 九、目前无法独立验证的内容

本次上传主要是文档与 manifest，没有上传：

* `smooth_atmosphere.py`；
* `solve_feasibility_collocation_no_wind.py`；
* `configs/default.yaml`；
* 三张 dry-run CSV；
* `tests/test_q3_gate2_readiness.py`。

因此目前可以确认：

* 文档之间基本一致；
* 结果声明没有明显自相矛盾；
* 数值量级看起来合理。

但不能独立确认：

* C1 温度曲线是否真正满足端点导数；
* 压力积分是否严格静力一致；
* 配点缺陷是否按声明的尺度计算；
* warm start 是否确实重新推进了 (m,t)；
* (h_{\max}) dry-run 表的具体内容；
* 测试是否实际覆盖了上述逻辑。

在脚本和 CSV 未审查前，不建议把 `reproducible` 改为 `true`。

---

## 下一阶段唯一主任务

现在应直接完成：

```text
solve_feasibility_collocation_no_wind.py
```

的非 dry-run 分支。

执行顺序：

1. (N=31)，以投影后的 Gate 1 为初值；
2. 第一阶段只求
   [
   \min s;
   ]
3. 若通过，再固定
   [
   s\le s_{\min}+10^{-3}\ \mathrm{kg}
   ]
   求控制平滑；
4. 运行 (N=61,121)；
5. 对
   [
   h_{\max}=10950,11500,12000,12500\ \mathrm m
   ]
   分别重新优化；
6. 只有满足全部预设阈值，才进入无风燃油最优问题。

---

## 最终判断

| 项目                  | 评价                  |
| ------------------- | ------------------- |
| C1 大气设计             | 正确                  |
| C1 大气数值证据           | 部分完成                |
| warm-start 重新投影     | 设计正确                |
| Gate 2 dry-run      | 已成功运行               |
| dry-run 质量缺口        | 14.197 kg           |
| dry-run 配点缺陷        | (6.20\times10^{-5}) |
| Gate 2 是否通过         | 否，尚未优化              |
| PMP 终端条件            | 已修正                 |
| 高度边界弧说明             | 已修正                 |
| 航程域 KKT 口径          | 正确                  |
| collocation 离散格式    | 仍需明确冻结              |
| (h_{\max}) 灵敏度      | 当前仅 warm-start 诊断   |
| 正式无风最优求解            | 尚不能开始               |
| 是否可以运行正式 Gate 2 NLP | 可以                  |

**结论：这一版已经不是“继续审计文档”的阶段，而是可以正式运行可行性 NLP 的阶段。**

最需要避免的是把：

[
\text{dry-run sensitivity}
]

误写成：

[
\text{optimized sensitivity},
]

以及把：

[
6.20\times10^{-5}
]

的初始缺陷误写成配点求解已经收敛。
