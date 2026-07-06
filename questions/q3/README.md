# q3 — 小问 3

- 状态：`in_design`
- 负责人：Codex
- 依赖小问：q1 等速参考路径、q2 共同可行航程
- 正式入口：`python questions/q3/scripts/pipeline.py --dry-run`

## 任务目标

建立第三问最优控制模型的题意审计、优化问题定义、必要条件推导和直接法数值求解方案；本轮不生成正式最优轨迹和最优油耗数值。

## 输入

- 数据：`question.md`
- 上游结果：`artifacts/q1/data/constant_speed_profile.csv`、`artifacts/q2/data/q2_fuel_summary.csv`
- 参数 / 配置：`configs/default.yaml`

## 输出

- 核心数值或决策：固定比较航程 `Xf=189781.310 m`；终端高度 `h(tf)=10577.124 m`；终端速度 `V(tf)=240 m/s`
- 结果表：本轮不生成正式结果表
- 图：本轮不生成论文级图
- 生图数据：本轮不生成生图数据

## 完成条件

- [x] 题意和数学目标明确
- [x] 优化问题定义完成
- [x] 必要条件推导完成
- [x] 直接法求解方案完成
- [x] 验证计划完成
- [ ] 正式求解脚本完成
- [ ] 数值最优结果完成
- [ ] 图表和数据成对保存
- [ ] 支持性证据链完成
