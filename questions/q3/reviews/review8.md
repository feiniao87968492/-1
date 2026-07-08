是的，**现在可以进入正式数值求解了**。

前置问题已经基本关闭：

* C1 大气已经验证进入密度—阻力—速度动力学链路；
* 所需推力口径下，大气差异也能继续传导到燃油率；
* 静力残差完成了独立有限差分和步长敏感性检查；
* 已规定正式求解必须报告独立 ODE 重积分误差；
* 梯形法的中点检查、第二阶段硬质量约束也已经冻结。

但这里的“正式数值求解”应先指：

[
\boxed{\text{非 dry-run 的 Gate 2 无风可行性 NLP}}
]

还不是直接求最终无风最省油轨迹，更不能直接跳到有风问题。

## 建议执行顺序

### 1. 首次正式求解

采用：

[
N=31,\qquad h_{\max}=12000\ \mathrm m,
]

航程域梯形配点，第一阶段目标仅为：

[
\min s
]

约束：

[
m(X_f)+s\ge62000,\qquad s\ge0.
]

不要在第一阶段加入控制平滑权重。

### 2. Gate 通过标准

必须同时满足：

[
s\le0.05\ \mathrm{kg},
]

[
|\delta_{\mathrm{trap}}|_\infty\le10^{-6},
]

[
|h_f-10577.124|\le0.1\ \mathrm m,
]

[
|V_f-240|\le10^{-3}\ \mathrm{m/s},
]

以及无量纲状态、控制约束违反不超过：

[
10^{-6}.
]

此外还要通过独立高精度 ODE 重积分，至少报告：

* `reintegration_state_error_inf`
* `reintegration_terminal_mass_error_kg`
* `reintegration_terminal_height_error_m`
* `reintegration_terminal_speed_error_mps`

这些诊断已在本轮设计中明确要求。

### 3. 第二阶段控制平滑

若第一阶段得到严格可行解，第二阶段应固定：

[
s=0
]

或直接取消松弛变量并施加硬约束：

[
m_f\ge62000-\epsilon_{\mathrm{num}}.
]

然后才最小化控制变化：

[
R=
\sum_i(T_{i+1}-T_i)^2
+
w_\gamma\sum_i(\gamma_{i+1}-\gamma_i)^2.
]

不能重新允许：

[
s\le10^{-3}\ \mathrm{kg}
]

来换取更平滑控制。

### 4. 网格收敛

依次运行：

[
N=31,\quad61,\quad121.
]

比较：

[
s_N,\quad m_f^{(N)},\quad t_f^{(N)},
]

配点缺陷、重积分误差以及活跃约束。

只有结果随网格稳定，才能确认不是粗网格伪可行。

### 5. 高度上界正式敏感性

对以下四个高度上限分别**重新优化**：

[
h_{\max}\in
{10950,11500,12000,12500}\ \mathrm m.
]

输出真正的：

```text
optimized_hmax_sensitivity.csv
```

不能继续使用 warm-start 表代替优化后结果。当前文档也已经明确区分了两者。

### 6. Gate 2 通过之后

再进入正式无风燃油优化：

[
\min(m_0-m_f)
]

以 Gate 2 可行轨迹作为初值，并继续保留：

* 固定终端高度和速度；
* 飞行包线；
* C1 平滑大气；
* 独立重积分；
* 网格加密；
* 多初值；
* 怠速推力和时间约束敏感性。

最后才用无风最优解 continuation 到有风问题。

## 求解失败时的处理

若 (N=31) 首次失败，不应立即改题或放宽质量约束。优先使用：

1. 当前 Gate 1 投影轨迹；
2. 逐步降低动力学缺陷容差；
3. 先求纯可行问题，再恢复质量目标；
4. 从较宽松的 (h_{\max}) 或较短航程 continuation 回目标配置；
5. 多初值与变量尺度检查。

若在 (N=31/61/121)、多初值及不同 (h_{\max}) 下始终得到：

[
s^\star>0,
]

才有理由讨论当前边界条件下问题可能不可行。

## 当前结论

现有文档仍明确说明完整 collocation 尚未运行，dry-run 结果不能支持可行性或最优性结论。

因此下一轮应停止继续增加 readiness 审计，直接实现和运行：

```bash
python questions/q3/scripts/solve_feasibility_collocation_no_wind.py \
  --config configs/default.yaml \
  --nodes 31
```

核心目标只有一个：

[
\boxed{
\text{先得到经过重积分和网格验证的严格无风可行轨迹}
}
]
