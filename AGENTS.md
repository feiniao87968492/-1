# Agent Operating Rules — 实训1

本文件是本仓库的 Agent 主指令。`agent.md` 仅作为兼容入口。

## 0. 总目标

产出一套可复现、可验证、可写入论文的数学建模解决方案。代码、数据、图表和结论必须形成完整证据链。

## 1. 每次开始工作前

按顺序阅读：

1. `README.md`；
2. `docs/problem_statement.md`；
3. `docs/modeling_contract.md`；
4. 当前小问的 `README.md`、`approach.md` 和 `manifest.yaml`；
5. `devlog.md` 最近三条记录；
6. `docs/evidence_chain.csv` 中当前小问的记录。

若题意、数据、单位或目标仍不明确，先在文档中显式记录歧义和采用的解释，不要直接用代码掩盖问题。

## 2. 强制建模逻辑

每个小问必须形成：

```text
任务重述
→ 数学目标与评价指标
→ 符号、单位和约束
→ 数据来源与质量审计
→ 假设及其影响
→ 简单基线
→ 候选模型比较
→ 主模型与参数依据
→ 实验设计
→ 验证、诊断和灵敏度分析
→ 图表与数据产物
→ 结论、适用范围和局限
```

任何一步缺失，都不得把小问标记为 `done`。

## 3. 编码规则

- 所有正式脚本必须能从仓库根目录执行。
- 路径使用 `pathlib`，不得依赖手工切换工作目录。
- 随机种子放在 `configs/default.yaml`，不得在多个脚本中随意重复定义。
- 共享逻辑放入 `src/modeling_common/`，不要跨小问复制粘贴。
- 原始数据只读；处理结果写入 `data/interim/` 或 `data/processed/`。
- 探索性 Notebook 不能成为唯一结果来源。
- 关键函数应有类型提示、文档字符串和合理的异常处理。
- 对输入数据执行字段、类型、范围、缺失值和单位检查。
- 不静默吞掉错误，不以空数据或默认值继续生成看似正常的结果。

## 4. 模型规则

- 先建立可解释基线，再引入复杂模型。
- 选择主模型时记录候选方案和淘汰理由。
- 每个参数必须说明来源：题目给定、数据估计、文献、经验设置或搜索得到。
- 权重、阈值、惩罚系数和边界值必须进入配置或清晰定义。
- 预测模型必须防止数据泄漏。
- 优化模型必须检查可行性、约束满足和极端场景。
- 仿真必须固定种子、重复运行并报告不确定性。
- 多指标评价必须测试权重变化对排名的影响。
- 不将相关性表述为因果性，除非证据足以支持。

## 5. 产物规则

- 图片：`questions/qN/artifacts/figures/<stem>.png`
- 生图数据：`questions/qN/artifacts/figure_data/<stem>.csv`
- 图元数据：`questions/qN/artifacts/figure_data/<stem>.meta.json`
- 结果表：`questions/qN/artifacts/tables/<stem>.csv`
- 模型对象：`questions/qN/artifacts/models/`

优先调用：

```python
from modeling_common.artifacts import save_figure_bundle, save_table
```

生成论文级图表后，更新 `docs/figure_table_registry.csv`。

## 6. 证据链规则

每个论文级主张必须在 `docs/evidence_chain.csv` 中登记。状态为 `supported` 时必须填写：

- 数据来源；
- 脚本；
- 配置；
- 产物；
- 验证方式。

被推翻的主张保留并标为 `rejected` 或 `superseded`，不要删除实验历史。

## 7. 文档更新规则

完成有意义的工作单元后更新：

- 当前小问 `experiments.md`；
- 当前小问 `results.md`；
- `devlog.md`；
- 对应证据链和图表登记表；
- 有新决策时更新 `docs/decision_log.md`；
- 有新增风险时更新 `docs/risk_register.md`。

## 8. Git 规则

- 不覆盖用户已有文件。
- 不提交密钥、虚拟环境、缓存和无来源的大文件。
- 提交应小而明确，格式建议：
  - `docs: clarify q2 objective`
  - `feat(q1): add baseline model`
  - `feat(q3): implement optimization pipeline`
  - `test(q2): add sensitivity analysis`
  - `fix(data): correct unit conversion`
- 提交前运行 `python scripts/check_repo.py`。

## 9. 完成门槛

将小问状态改为 `done` 前，必须确认：

- 正式脚本可运行；
- 结果可复现；
- 有基线比较；
- 有验证和灵敏度分析；
- 图表和数据成对保存；
- 证据链完整；
- `results.md` 写明结论与局限；
- 自检无错误。

## 10. 禁止事项

- 禁止为迎合预期结论而修改数据。
- 禁止只保留最好的一次随机结果。
- 禁止用复杂度替代正确性。
- 禁止只保存图片而不保存生图数据。
- 禁止把未验证推断写成确定事实。
- 禁止在没有更新文档和证据链时宣称任务完成。
