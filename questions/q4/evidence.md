# q4 证据说明

本文件解释本小问关键主张的证据。机器可读索引仍以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q4-C01 | q4 采用固定共同航程比较油耗，并用固定燃油口径补充航程变化 | `question.md`、`docs/problem_statement.md`、`questions/q4/approach.md` | 文档审计 | 两个口径不能混写；固定燃油只支持下界估计 | supported |
| Q4-C02 | q4 等速基线复用 q1/q2 产物并登记到 q4 策略对比表 | q1/q2 supported artifacts；`questions/q4/artifacts/tables/strategy_comparison.csv` | q4 pipeline 复现检查 | 当前未单独输出 `baseline_summary.csv`，基线行位于 q4-T03 | supported |
| Q4-C03 | q4 已生成有风固定航程局部射击轨迹并通过终端状态、质量、约束和燃油恒等式验证 | `questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv`；`questions/q4/artifacts/tables/wind_optimal_results.csv`；`questions/q4/artifacts/tables/wind_optimal_trajectory.csv` | `python questions/q4/scripts/pipeline.py --config configs/default.yaml --nodes 41 --control-knots 5 --maxiter 300 --sensitivity-maxiter 80 --range-maxiter 80`；`python -m pytest tests/test_q4_pipeline.py -q` | 低维控制结点局部解，不支持全局最优 | supported |
| Q4-C04 | q4-T03 报告固定航程油耗节省，并记录相对 q1 等速全航程的参考航程差 | `questions/q4/artifacts/tables/strategy_comparison.csv` | q4 pipeline 与回归测试 | 固定燃油航程变化由 Q4-C07 单独支持，不与固定航程节油混写 | supported |
| Q4-C05 | q4 至少选择温度实时修正和发动机安装损失作为扩展框架 | `questions/q4/artifacts/tables/extension_frameworks.csv` | 表内包含 `framework_only` 状态、模型变化、数据需求和验证接口 | 仅为框架，非数值最优结果 | supported |
| Q4-C06 | q4-T04 对 `beta` 执行逐场景重新求解灵敏度，而不是标称轨迹后验重算 | `questions/q4/artifacts/tables/beta_sensitivity.csv` | 五档均 `reoptimization_performed=True`、`post_solution_metric_only=False` 且 `validation_status=passed` | 非标称场景优化器未成功终止，只支持局部可行敏感性 | supported_limited |
| Q4-C07 | q4-T06 在固定燃油 `10450 kg` 口径下给出局部航程下界估计 | `questions/q4/artifacts/tables/fixed_fuel_range.csv`；`questions/q4/artifacts/tables/fixed_fuel_range_trials.csv` | 三个航程因子均通过燃油预算和终端状态检查 | 未出现不可行/超预算括区，`201168.189 m` 不是严格最大航程 | supported_limited |
| Q4-C08 | q4 已生成三张论文级图及同名生图数据和元数据 | `questions/q4/artifacts/figures/*.png`；`questions/q4/artifacts/figure_data/*.csv`；`questions/q4/artifacts/figure_data/*.meta.json` | `python questions/q4/scripts/visualize.py`；`test_q4_visualize_exports_paper_figure_bundles` | 图片审美和论文排版仍可在最终成文阶段微调 | supported |
