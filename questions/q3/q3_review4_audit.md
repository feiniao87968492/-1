# q3 review4 对照审计

来源：`questions/q3/review4.md`

## 结论

review4 合理。上一轮已经完成 Gate 2 前的总体口径冻结，本轮不继续扩写总方案，也不生成正式无风最优解；本轮完成 Gate 2 编码前的可验证基础设施：静力一致 C1 平滑大气、Gate 2 dry-run 入口、warm start 重新投影、无量纲违约尺度、manifest 入口和 PMP 边界条件修订。

## 逐项处理

| 编号 | review4 意见 | 状态 | 本轮处理 |
|---|---|---|---|
| R1 | C1 大气平滑不能只写过渡带，必须说明平滑变量并保持静力一致 | fixed | 新增 `questions/q3/scripts/smooth_atmosphere.py`：只平滑温度曲线，压力由 `dp/dh=-rho g` 积分，密度和声速由状态方程计算 |
| R2 | 终端质量不等式下 PMP 横截条件需加入乘子 | fixed | `derivation.md` 修正为 `lambda_m(tf)=-1-nu`，并说明 `nu=0` 时才退化为 `-1` |
| R3 | 高度上界激活时连续 PMP 需要边界弧条件 | fixed | `derivation.md` 补充 `h=h_max` 边界弧的切向条件 `dot h=V sin gamma=0` 和分段结构限制 |
| R4 | Gate 阈值需明确尺度，`epsilon_s` 需给出数值 | fixed | `configs/default.yaml` 写入 `constraint_violation_scale: nondimensional` 和 `slack_smoothing_tolerance_kg: 1e-3` |
| R5 | Gate 1 轨迹只能 warm start，不能直接作为 Gate 2 可行状态 | fixed | 新增 `solve_feasibility_collocation_no_wind.py --dry-run`，将 Gate 1 `(h,V,T,gamma)` 投影到 C1 大气并重新推进 `m,t` |
| R6 | 航程域 Hamiltonian 方向正确 | frozen | 保留 `derivation.md` 中的航程域 KKT/Hamiltonian 口径 |
| R7 | manifest 需增加 Gate 2 正式入口和产物 | fixed | `manifest.yaml` 增加 `feasibility_collocation_no_wind` 入口、三张 Gate 2 表和质量门禁 |
| R8 | 状态保持 `in_design` 仍可接受 | fixed | 未改为 `done`；Gate 2 dry-run 不是完整优化 |

## dry-run 结果边界

`python questions/q3/scripts/solve_feasibility_collocation_no_wind.py --config configs/default.yaml --nodes 21 --dry-run` 已生成：

- `questions/q3/artifacts/tables/no_wind_collocation_gate.csv`
- `questions/q3/artifacts/tables/no_wind_collocation_trajectory.csv`
- `questions/q3/artifacts/tables/no_wind_hmax_sensitivity.csv`

该 dry-run 只验证新模型下的投影和诊断链，不最小化 `s`，不能用作严格可行性或最优性结论。
