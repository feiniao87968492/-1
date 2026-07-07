# q3 review2 对照审计

来源：`questions/q3/review2.md`

## 结论

review2 合理。上一轮已经完成设计审查和固定路径预检查；本轮按 review2 要求进入 Gate 1：无风可行性求解，而不是直接生成最终无风最优轨迹。

本轮新增 `questions/q3/scripts/solve_feasibility_no_wind.py`。该脚本采用航程域低维参数化可行性搜索，固定端点和飞行包线，最小化终端质量松弛：

```text
min s
m(Xf)+s >= 62000,  s >= 0
```

输出表明，在当前参数化搜索和现有边界下，质量缺口从固定路径的 `836.526 kg` 降至 `10.214 kg`，但仍未达到 `s=0`，因此状态为 `needs_relaxation`。这不是无风问题不可行证明，只是说明当前 Gate 1 尚未构造出严格可行轨迹。

## 逐项处理

| 编号 | review2 意见 | 状态 | 本轮处理 |
|---|---|---|---|
| R1 | 固定路径无风不可行不能证明整个无风问题不可行 | fixed | `results.md` 和证据链保持该限定；新增可行性 Gate，不直接缩短航程 |
| R2 | `m>=62000` 应改为终端不等式 | fixed | `approach.md`、`derivation.md` 和配置改为 `mass_constraint: terminal_only` |
| R3 | 控制变化率口径仍冲突 | fixed | 第一版主实现明确不加严格变化率约束，只用控制边界和平滑正则；严格变化率留给扩展状态版本 |
| R4 | 直接求解建议改为航程域 | fixed | 新增 `solve_feasibility_no_wind.py`，状态为 `(h,V,m,t)`，独立变量为 `x` |
| R5 | 数值飞行包线仍需冻结 | partial | 主边界仍读取 `configs/default.yaml`；已记录来源为仿真假设，正式最优前仍需敏感性 |
| R6 | 零推力问题尚未解决 | partial | Gate 1 记录最小推力且当前轨迹未贴近 `T=0`；正式最优前仍需 `T_idle` 敏感性 |
| R7 | PMP 诊断缺少伴随变量来源 | planned | 文档补充以 NLP 缺陷约束乘子为首选来源；当前 Gate 1 不做 PMP 诊断 |
| R8 | `t_base` 要按无风/有风场景区分 | fixed | `results.md` 记录无风基准时间 `790.755 s`、有风基准时间 `721.753 s` |
| R9 | 状态仍应保持 `in_design` | fixed | q3 manifest 仍为 `in_design`，不标记 done |

## Gate 1 结果

| 指标 | 数值 |
|---|---:|
| 固定路径质量缺口 | 836.526 kg |
| Gate 1 最小质量缺口 | 10.214 kg |
| Gate 1 终端质量 | 61989.786 kg |
| Gate 1 总时间 | 802.883 s |
| 非松弛约束最大违反 | 0.000 |
| 积分一致性残差 | 6.94e-18 |
| 状态 | needs_relaxation |

产物：

- `questions/q3/artifacts/tables/no_wind_feasibility_gate.csv`
- `questions/q3/artifacts/tables/no_wind_feasibility_trajectory.csv`

## 下一步

1. 扩展 Gate 1 参数化或改为完整 collocation NLP，目标仍是让 `s*` 接近 0。
2. 若多初值和加密网格后仍 `s*>0`，再讨论缩短航程或调整质量约束口径。
3. 只有当 `s*≈0` 时，才进入 `solve_no_wind.py` 的正式无风最优求解。
