# q2 — 小问 2

- 状态：`done`
- 负责人：Codex
- 依赖小问：q1 等速参考航程
- 正式入口：`python questions/q2/scripts/pipeline.py --config configs/default.yaml`

## 任务目标

在 q1 等速策略参考航程 `200668.442 m` 下，建立基于连续标准大气的固定航程燃油路径积分模型，并比较标准 ISA 与常温偏差静力平衡修正下的总油耗和沿路径油耗率分布。

## 输入

- 数据：`question.md`、题设参数、q1 等速参考航程
- 上游结果：`artifacts/q1/data/strategy_comparison.csv`
- 参数 / 配置：`configs/default.yaml`

## 输出

- 核心数值或决策：`artifacts/q2/data/q2_fuel_summary.csv`、`artifacts/q2/data/q2_temperature_sensitivity.csv`
- 结果表：`questions/q2/artifacts/tables/`
- 图：`questions/q2/artifacts/figures/`
- 生图数据：`questions/q2/artifacts/figure_data/`

## 完成条件

- [x] 题意和数学目标明确
- [x] 基线完成
- [x] 主模型完成
- [x] 验证与诊断完成
- [x] 灵敏度或不确定性分析完成
- [x] 图表和数据成对保存
- [x] 证据链更新
- [x] `results.md` 完成
