## 总体评价

**这版已经把 Gate 2 dry-run 的证据链补得比较完整，具备直接实现非 dry-run NLP 的条件。**

相较上一版，主要改进都有效：

* Gate 1 到 Gate 2 的质量差异已拆分；
* C1 大气增加了静力残差、正值性和相对分层 ISA 偏差；
* `h_max` 文件明确改称 warm-start 诊断；
* 当前离散格式冻结为航程域梯形配点；
* 没有在 dry-run 阶段伪造 KKT 乘子或最优性结论。

当前项目状态改成 `in_implementation` 是合理的。但这仍然只是：

[
\text{可运行的 NLP 初值与诊断基础设施}
]

而不是：

[
\text{已求解的 collocation 可行性问题}.
]

---

# 一、投影差异现在基本解释清楚

目前三阶段投影结果是：

[
m_f^{A}=61989.785554\ \mathrm{kg},
]

[
m_f^{B}=61985.803328\ \mathrm{kg},
]

[
m_f^{C}=61985.803328\ \mathrm{kg}.
]

其中：

* A：原 Gate 1 轨迹；
* B：插值到 Gate 2 网格、仍使用原分层 ISA 后重新积分；
* C：切换到 C1 平滑大气后重新积分。

因此：

[
\Delta m_{\mathrm{grid}}
========================

# m_f^A-m_f^B

3.982226\ \mathrm{kg},
]

而文档报告：

[
\Delta m_{\mathrm{atmos}}=0.
]



这至少说明原来约 (3.983\ \mathrm{kg}) 的差异主要来自：

* 网格插值；
* 控制重采样；
* 重新积分方式；

而不是简单归因于大气层平滑。

这个审计思路是正确的。

---

# 二、但“大气切换质量差异精确为 0”仍值得专项检查

C1 大气相对于分层 ISA 已经存在非零偏差：

[
\Delta T_{\max}=0.08125\ \mathrm K,
]

[
\Delta p_{\max}=0.044253\ \mathrm{Pa},
]

[
\Delta \rho_{\max}
==================

1.36\times10^{-4}\ \mathrm{kg/m^3}.
]



而轨迹又确实穿越 11 km 平滑区。理论上，密度变化会通过阻力：

[
D
=

\frac12\rho V^2SC_{D0}
+
\frac{2km^2g^2\cos^2\gamma}
{\rho V^2S}
]

影响推力需求和质量积分。

所以 (m_f^B) 与 (m_f^C) 完全相同到六位小数，有三种可能：

1. 大气影响确实极小，小于当前输出精度；
2. 两种投影过程实际上共用了同一组密度；
3. C1 大气已经生成，但没有真正接入质量投影所调用的气动函数。

## 建议增加最小单元测试

在平滑区固定：

[
h=11000\ \mathrm m,\quad
V=235\ \mathrm{m/s},\quad
m=67000\ \mathrm{kg},\quad
\gamma=0,
]

分别计算：

[
\rho_{\mathrm{layer}},\quad
\rho_{C1},
]

[
D_{\mathrm{layer}},\quad
D_{C1},
]

[
\frac{dm}{dx}*{\mathrm{layer}},
\quad
\frac{dm}{dx}*{C1}.
]

要求：

* 差值能被直接观察到；
* 投影代码确实调用选择的大气模型；
* A/B/C 表至少输出 9～12 位小数。

在这项测试通过前，“C1 大气对投影质量没有影响”不能写成物理结论，只能写成当前数值精度下未观察到差异。

---

# 三、静力残差 (2.22\times10^{-16}) 很好，但可能属于构造恒等式

当前报告：

[
r_{\mathrm{hyd}}\approx2.22\times10^{-16}.
]



若残差是用构造公式：

[
\frac{dp}{dh}
=============

-\frac{gp}{RT}
]

直接代回：

[
\frac{dp}{dh}+\rho g
]

计算，那么得到机器精度并不意外，因为：

[
\rho=\frac{p}{RT}.
]

这只能证明公式内部一致，不能证明：

* 压力数值积分准确；
* 插值后的 (p(h)) 仍满足静力方程；
* 自动微分或有限差分得到的 (dp/dh) 正确。

## 更有说服力的审计

在密集高度网格上，用实际生成的压力函数做独立数值微分：

[
\left(\frac{dp}{dh}\right)_{\mathrm{num}}
]

然后计算：

[
r_{\mathrm{hyd,num}}
====================

\max_h
\frac{
\left|
(dp/dh)_{\mathrm{num}}+\rho g
\right|
}{
\rho g
}.
]

同时报告：

* 最大值；
* 均方值；
* 最大值发生高度；
* 平滑带端点处的残差。

这一残差大概率不会达到 (10^{-16})，但它更能验证实际代码。

---

# 四、梯形离散口径已经冻结，建议正式 Gate 2 也先保持梯形

当前已经明确：

[
\texttt{collocation_transcription: trapezoidal}.
]

并说明 Hermite–Simpson 只是候选升级。

这是正确修订。

建议第一轮正式 NLP 不要立即切换到 Hermite–Simpson。否则会同时改变：

* 优化模型；
* 缺陷公式；
* 中点状态定义；
* warm start 投影；
* 缺陷阈值解释。

更稳妥的顺序是：

1. 用梯形法完成 (N=31) 正式可行性 NLP；
2. 梯形法加密到 (N=61,121)；
3. 得到稳定结果后，再用 Hermite–Simpson 独立复核；
4. 两种方法分别报告缺陷，不能直接比较同一个 `scaled_collocation_defect_inf`。

文档现在已经正确区分两种缺陷口径。

---

# 五、当前 dry-run 数值仍然只是初值质量

目前 dry-run：

[
s=14.196672\ \mathrm{kg},
]

[
|\delta_{\mathrm{col}}|_\infty
\approx6.20\times10^{-5}.
]

而通过阈值为：

[
s\le0.05\ \mathrm{kg},
]

[
|\delta_{\mathrm{col}}|_\infty\le10^{-6}.
]

所以当前分别相差约：

[
\frac{14.196672}{0.05}\approx284,
]

和：

[
\frac{6.20\times10^{-5}}{10^{-6}}=62.
]

这些数值没有任何“接近通过”的含义，只表示 warm start 对优化器来说不是特别差。审计文档继续使用：

```text id="nurmq5"
dry_run_not_optimized
```

是准确的。

---

# 六、`h_max` 文件命名已修复，但 Manifest 仍保留一个容易误解的兼容入口

文档已经将新文件明确命名为：

```text id="sqor4x"
warm_start_hmax_diagnostic.csv
```

并规定它不能支持：

[
s^\star(h_{\max})
]

结论。

这是正确的。

但 manifest 中仍同时存在：

```yaml id="3wm8h3"
hmax_sensitivity:
  questions/q3/artifacts/tables/no_wind_hmax_sensitivity.csv
```

以及：

```yaml id="s9cs44"
warm_start_hmax_diagnostic:
  questions/q3/artifacts/tables/warm_start_hmax_diagnostic.csv
```

旧文件虽然是兼容输出，但名称仍像正式优化灵敏度。

建议改为：

```yaml id="jtcg6g"
legacy_warm_start_hmax_diagnostic:
  questions/q3/artifacts/tables/no_wind_hmax_sensitivity.csv
```

正式结果预留：

```yaml id="g4ephs"
optimized_hmax_sensitivity:
  questions/q3/artifacts/tables/optimized_hmax_sensitivity.csv
```

否则后续论文脚本或汇总脚本可能误读旧表。

---

# 七、投影差异的来源还可以继续细分

目前 A 到 B 同时发生了：

* 控制插值；
* 节点数量变化；
* (h,V) 插值；
* 用新网格重新积分 (m,t)。

因此：

[
3.982226\ \mathrm{kg}
]

只能归类为“综合重采样/重积分差异”，不能严格只叫网格差异。

更精确的审计可以分为：

[
A_0:
\text{原网格、原状态、原控制},
]

[
A_1:
\text{新网格插值控制，但高精度连续积分},
]

[
A_2:
\text{新网格梯形积分},
]

[
A_3:
\text{新网格+C1大气}.
]

这样才能分别得到：

[
\Delta m_{\mathrm{control\ interpolation}},
]

[
\Delta m_{\mathrm{trapezoidal}},
]

[
\Delta m_{\mathrm{atmosphere}}.
]

不过这不是正式 NLP 的阻塞项，可以在正式求解器完成后再补。

---

# 八、终端 PMP 和边界弧修订已经到位

当前推导已经正确加入：

[
g_f=62000-m_f\le0,
]

[
\nu\ge0,
\qquad
\nu g_f=0,
]

[
\lambda_m(t_f)=-1-\nu.
]

也明确指出，高度边界弧上：

[
h=h_{\max},
\qquad
\dot h=V\sin\gamma=0,
]

因此在 (V>0) 时：

[
\gamma=0.
]



这一部分不需要继续扩写。

正式数值结果只需要如实区分：

* 连续 PMP 理论说明；
* 航程域离散 KKT 诊断；
* 活跃高度约束的 NLP 乘子。

---

# 九、证据链状态基本诚实

当前证据链将：

* Gate 1 数值；
* dry-run 可运行；
* 投影审计；
* C1 大气诊断；

标记为 `supported`，同时明确限制：

* 没有执行完整 NLP；
* warm-start 表不能支持 (s^\star(h_{\max}))；
* dry-run 缺陷不能作为 Gate 通过结论。

这部分质量较高。

`manifest` 中：

```yaml id="rx3tve"
status: in_implementation
```

也比之前的 `in_design` 更准确。

---

# 十、本次仍无法独立验证代码与 CSV

本次上传了文档和 manifest，但没有上传：

* `smooth_atmosphere.py`；
* `solve_feasibility_collocation_no_wind.py`；
* `configs/default.yaml`；
* 新增的三张 CSV；
* `test_q3_gate2_readiness.py`。

因此我能确认的是：

* 文档之间已经基本一致；
* 数值声明没有明显算术冲突；
* 证据边界表述合理。

但无法独立确认：

* C1 大气是否真的接入动力学；
* B→C 为 0 是否是正常数值结果；
* 静力残差是否为独立数值审计；
* 梯形缺陷实现是否和文档一致；
* warm-start 表中是否包含隐藏越界。

所以：

```yaml id="u65hbj"
reproducible: false
```

继续保留是正确的。

---

## 下一阶段

现在没有必要再做第六轮 dry-run 审计。应直接实现非 dry-run 分支：

[
\boxed{
\min s
}
]

满足完整梯形配点约束。

推荐顺序：

1. (N=31,\ h_{\max}=12000\ \mathrm m)；
2. 第一阶段只最小化 (s)；
3. 若 (s\le0.05\ \mathrm{kg})，再进行词典序平滑；
4. 加密到 (N=61,121)；
5. 分别重新优化
   [
   h_{\max}=10950,11500,12000,12500\ \mathrm m;
   ]
6. 保存真正的：

   ```text id="3i4n06"
   optimized_hmax_sensitivity.csv
   ```
7. 求解成功后再提取 NLP 乘子做航程域 KKT 诊断。

---

## 最终判断

| 项目                       | 评价            |
| ------------------------ | ------------- |
| dry-run 证据链              | 已基本闭环         |
| 投影差异审计                   | 已完成，仍可进一步细分   |
| C1 大气设计                  | 正确            |
| C1 大气是否真正接入动力学           | 需要代码级验证       |
| 静力残差                     | 数值优秀，但需独立差分验证 |
| 离散格式                     | 已冻结为梯形        |
| warm-start (h_{\max}) 命名 | 已修复           |
| Manifest 旧兼容名称           | 仍有轻微歧义        |
| Gate 2 正式 NLP            | 尚未实现          |
| 是否需要继续补文档                | 基本不需要         |
| 是否可以开始正式 NLP             | 可以            |
| 是否可以开始无风燃油最优             | 不可以           |

**结论：这一版已经把 dry-run 做到了足够完整。继续审查 dry-run 的边际价值很低，下一步必须真正运行优化器。**

当前最值得在编码时立即核查的是：

[
\boxed{
m_f^{B}=m_f^{C}
}
]

究竟表示 C1 大气影响确实低于输出精度，还是平滑大气尚未真正进入气动与质量积分链。
