# q4 结果与结论

## 1. 最终模型

- 模型：有风航程域点质量最优控制，主数值分支为 reduced-control shooting；推力和航迹角采用分段线性控制结点，状态由 ODE 连续积分。
- 相比基线的改进：在固定 q2 共同可行航程下，当前局部射击解相对 q2 标准 ISA 等速基线节省 `563.416 kg` 燃油，节省比例 `5.403%`。
- 关键参数：`Xf=189781.310 m`、`W(h)=20+3e-5(h-10000)^2`、`beta=0.003`、q3/q4 飞行包线边界。
- 主张强度：当前结果只支持“局部降维射击解”和“局部重求解敏感性”，不支持全局最优或严格最大航程表述。

## 2. 核心结果

| 指标 / 输出 | 数值 | 单位 | 产物 | Claim ID |
|---|---:|---|---|---|
| 固定航程主口径 | 189781.310 | m | `artifacts/q2/data/q2_fuel_summary.csv` | Q4-C01 |
| q2 标准 ISA 等速固定航程基线燃油 | 10427.256 | kg | `questions/q4/artifacts/tables/strategy_comparison.csv` | Q4-C02 |
| q4 有风局部射击燃油 | 9863.840 | kg | `questions/q4/artifacts/tables/wind_optimal_results.csv` | Q4-C03 |
| q4 终端质量 | 62586.160 | kg | `questions/q4/artifacts/tables/wind_optimal_results.csv` | Q4-C03 |
| q4 最终时间 | 733.758 | s | `questions/q4/artifacts/tables/wind_optimal_results.csv` | Q4-C03 |
| q4 节省燃油 | 563.416 | kg | `questions/q4/artifacts/tables/strategy_comparison.csv` | Q4-C04 |
| q4 油耗节省比例 | 5.403 | % | `questions/q4/artifacts/tables/strategy_comparison.csv` | Q4-C04 |
| 固定航程相对 q1 等速全航程差 | -10887.133 | m | `questions/q4/artifacts/tables/strategy_comparison.csv` | Q4-C04 |
| 固定燃油航程下界估计 | 201168.189 | m | `questions/q4/artifacts/tables/fixed_fuel_range.csv` | Q4-C07 |
| 固定燃油航程增量下界 | 11386.879 | m | `questions/q4/artifacts/tables/fixed_fuel_range.csv` | Q4-C07 |
| 固定燃油航程增量比例 | 6.000 | % | `questions/q4/artifacts/tables/fixed_fuel_range.csv` | Q4-C07 |
| 扩展框架数量 | 2 | 项 | `questions/q4/artifacts/tables/extension_frameworks.csv` | Q4-C05 |
| 论文级图表数量 | 3 | 张 | `questions/q4/artifacts/figures/` | Q4-C08 |

## 3. 验证结果

- 验证方法：复现上游基线、独立 ODE 重积分、终端误差、连续路径约束、燃油恒等式、控制结点收敛、多初值一致性、风场开关回归，以及图表数据/元数据配对检查。
- q4-T02/q4-T03 是否通过：通过当前局部解验证。终端高度误差 `6.31e-7 m`，终端速度误差 `1.51e-8 m/s`，最大尺度化约束违反 `0`，燃油恒等式残差 `0.0316 kg`。
- q4-T04 是否通过：五个 `beta` 场景均重新求解并通过终端/约束验证；但非标称场景 SLSQP 返回 `Iteration limit reached`，因此只支持局部可行敏感性，不支持强最优性敏感性。
- q4-T06 是否通过：`1.00/1.03/1.06` 三个航程因子均通过固定燃油预算检查；`1.06` 仍剩余 `49.393 kg` 燃油，状态为 `lower_bound_no_infeasible_bracket`，因此不是严格最大航程。

## 4. 灵敏度与稳健性

| `beta` 因子 | 燃油 | 相对标称变化 | 验证状态 | 优化器成功 |
|---:|---:|---:|---|---|
| 0.8 | 9849.724 kg | -14.116 kg | passed | False |
| 0.9 | 9852.888 kg | -10.953 kg | passed | False |
| 1.0 | 9863.840 kg | 0.000 kg | passed | True |
| 1.1 | 9869.462 kg | +5.621 kg | passed | False |
| 1.2 | 9870.070 kg | +6.230 kg | passed | False |

解释边界：五档均设置 `reoptimization_performed=True` 且 `post_solution_metric_only=False`；非标称行不应写成“已收敛最优解”，只能写成当前参数化和迭代预算下的局部可行响应。

## 5. 可写入论文的结论

- 在配置风场 `W(h)=20+3e-5(h-10000)^2`、固定共同航程 `189781.310 m` 和当前 reduced-control shooting 参数化下，有风局部优化轨迹燃油为 `9863.840 kg`，比 q2 标准 ISA 等速固定航程基线少 `563.416 kg`，相对节省 `5.403%`。
- 固定燃油 `10450 kg` 口径下，当前局部航程网格支持可达航程至少 `201168.189 m`，较固定共同航程增加 `11386.879 m`；该数值是下界估计，不是最大航程证明。
- `beta` 从标称值降低到 `0.8` 倍时，当前局部可行解燃油减少 `14.116 kg`；增加到 `1.2` 倍时燃油增加 `6.230 kg`。由于非标称场景未取得优化器成功终止标志，该结论只可作为局部敏感性描述。

## 6. 局限与适用范围

- 当前 q4-T02 采用 5 个控制结点和 41 个输出节点；更高维控制参数化、多初值和稀疏 NLP 交叉验证尚未完成。
- “燃油节省比例”和“航程变化”的公平比较口径不同，本轮采用固定航程为主、固定燃油为辅。
- 固定燃油航程试验未括住不可行或超预算上界，`201168.189 m` 只能写成局部下界估计。
- `beta` 非标称场景虽然通过可行性验证，但优化器未成功终止，不能外推为严格最优敏感性。
- 扩展框架表只给出模型接口、数据需求和验证计划，不是已完成的温度实时修正或发动机安装损失数值优化。

## 7. 复现命令

```bash
python questions/q4/scripts/pipeline.py --config configs/default.yaml --nodes 41 --control-knots 5 --maxiter 300 --sensitivity-maxiter 80 --range-maxiter 80
python questions/q4/scripts/visualize.py
python -m pytest tests/test_q4_pipeline.py -q
```
