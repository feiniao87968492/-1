# q1 — 小问 1

- 状态：`done`
- 负责人：Codex
- 依赖小问：无
- 正式入口：`python questions/q1/scripts/pipeline.py --config configs/default.yaml`

## 任务目标

在固定终止质量下比较等真空速与等马赫数巡航爬升策略的时间、航程、最终高度、爬升率和固定燃油消耗。

## 输入

- 数据：题面参数、`question.md`、`questions/q1/brief.md`
- 上游结果：无
- 参数 / 配置：`configs/default.yaml`

## 输出

- 核心数值或决策：`artifacts/q1/data/strategy_comparison.csv`
- 结果表：`questions/q1/artifacts/tables/`
- 图：`questions/q1/artifacts/figures/`
- 生图数据：`questions/q1/artifacts/figure_data/`

## 完成条件

- [x] 题意和数学目标明确
- [x] 基线完成
- [x] 主模型完成
- [x] 验证与诊断完成
- [x] 灵敏度或不确定性分析完成
- [x] 图表和数据成对保存
- [x] 证据链更新
- [x] `results.md` 完成
