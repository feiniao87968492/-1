# q4 — 小问 4

- 状态：`done`
- 负责人：Codex
- 依赖小问：q1 等速策略基线；q2 共同可行航程和温度修正；q3 无风最终优化结果
- 正式入口：`python questions/q4/scripts/pipeline.py --config configs/default.yaml`

## 任务目标

在前三问基础上建立综合数值模型，统一复现实等速巡航爬升基线、求解有风局部优化高度-速度轨迹，报告固定航程油耗节省、固定燃油航程变化、`beta` 灵敏度和两个模型扩展框架。

## 输入

- 数据：`question.md`
- 上游结果：
  - `artifacts/q1/data/constant_speed_profile.csv`
  - `artifacts/q1/data/strategy_comparison.csv`
  - `artifacts/q2/data/q2_fuel_summary.csv`
  - `questions/q3/artifacts/tables/no_wind_final_optimal_results.csv`
  - `questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv`
- 参数 / 配置：`configs/default.yaml`

## 输出

- 核心数值或决策：等速基线、考虑风场的局部优化轨迹、油耗节省比例、航程变化、`beta` 灵敏度、温度实时修正和发动机安装损失扩展框架。
- 结果表：`questions/q4/artifacts/tables/`
  - `wind_optimal_results.csv`
  - `wind_optimal_trajectory.csv`
  - `strategy_comparison.csv`
  - `beta_sensitivity.csv`
  - `fixed_fuel_range.csv`
  - `fixed_fuel_range_trials.csv`
  - `extension_frameworks.csv`
- 图：`questions/q4/artifacts/figures/`
  - `height_range_comparison.png`
  - `profile_comparison.png`
  - `beta_sensitivity.png`
- 生图数据：`questions/q4/artifacts/figure_data/`

## 完成条件

- [x] 题意和数学目标明确
- [x] 基线完成
- [x] 有风主模型完成
- [x] 验证与诊断完成
- [x] `beta` 灵敏度或不确定性分析完成
- [x] 至少两个扩展框架完成
- [x] 图表和数据成对保存
- [x] q4-T02/q4-T03/q4-T04/q4-T05/q4-T06 证据链更新
- [x] `results.md` 写入 q4-T02/q4-T03/q4-T04/q4-T06 结论与局限
- [x] 图表、生图数据和图元数据成对登记
