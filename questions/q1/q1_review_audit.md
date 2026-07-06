# q1 对照 `tasks/q1_review.md` 的审计

## 1. 审计结论

已对照 `tasks/q1_review.md` 逐项审核当前 q1 基线流水线。结论是：影响主结果可信度的代码问题已经修复并通过验证；若干建模建议已在文档中解释或作为后续扩展保留。当前 q1 仍应表述为“准稳态巡航爬升基线模型”，不能表述为真实飞机工程认证结论。

## 2. 已修复的实质问题

| 审查项 | 处理状态 | 当前证据 | 说明 |
|---|---|---|---|
| 平均爬升率和平均地速不能用自适应求解器采样点简单平均 | 已修复 | `questions/q1/scripts/simulate.py`, `artifacts/q1/data/strategy_comparison.csv` | `mean_climb_rate_mps=(h_f-h_0)/(t_f-t_0)`，`mean_groundspeed_mps=(x_f-x_0)/(t_f-t_0)`，避免受 `solve_ivp` 非均匀采样影响。 |
| 步长敏感性不应只检查最终高度 | 已修复 | `questions/q1/scripts/validate.py`, `questions/q1/artifacts/tables/validation_summary.csv` | 当前检查 `final_time_s`、`final_distance_m` 和 `mean_climb_rate_mps`，对应报告中的核心数值指标。 |
| 灵敏度扰动不应硬编码为 `beta ±20%` | 已修复 | `configs/default.yaml`, `questions/q1/scripts/validate.py`, `questions/q1/artifacts/tables/sensitivity_summary.csv` | 当前从 `validation.sensitivity_relative_changes` 读取 `[-20%, -10%, +10%, +20%]`，并保留 `cT=2.8e-5` 数量级对照。 |
| 残差阈值不应笼统写绝对残差 `1e-6` | 已修复 | `questions/q1/scripts/simulate.py`, `questions/q1/scripts/validate.py`, `questions/q1/derivation.md` | 升力和能量残差均为无量纲相对残差，验证表阈值按相对残差解释。 |
| 不应预设“等马赫爬升率更大” | 已遵守 | `questions/q1/results.md`, `docs/evidence_chain.csv` | 结果显示等速时间加权平均爬升率更高，结论按数值证据写入。 |
| `review.md` 状态过期 | 已修复 | `questions/q1/review.md` | 状态改为 `RESOLVED`，并记录已确认口径。 |
| 将 `gamma` 称为直接物理控制量不严谨 | 已修复 | `questions/q1/review.md`, `questions/q1/approach.md`, `questions/q1/derivation.md` | 统一表述为 `x,h,V,m` 是状态或轨迹变量，操作量可取 `T` 与 `CL/迎角`，`gamma` 由轨迹反算。 |
| 验证大部分属于代数自洽验证，需要补强独立诊断 | 已修复 | `questions/q1/scripts/validate.py`, `questions/q1/artifacts/tables/validation_summary.csv`, `questions/q1/results.md` | 新增小航迹角、隐式 ODE 分母、推力正性、等速解析终点和等马赫约束检查。 |
| 航程较大的原因表述不准确 | 已修复 | `artifacts/q1/data/strategy_comparison.csv`, `questions/q1/results.md` | 增加 `air_distance_m` 与 `wind_distance_contribution_m`，结论改为航程差异主要来自飞行时间，而非风速差异。 |

## 3. 已解释但未改变主模型的建议

| 审查项 | 处理状态 | 当前证据 | 说明 |
|---|---|---|---|
| 固定 `CL` 是人为闭合条件，需要说明依据 | 已补强说明 | `questions/q1/approach.md`, `questions/q1/derivation.md`, `docs/assumptions.md` | 已明确 `CL_ref` 是操作假设，并给出 `CL_ref=0.658914` 与 `sqrt(CD0/k)=0.699206` 的数量级比较。 |
| 大气模型存在“指数密度 + 标准声速”的混合 | 已列为局限 | `questions/q1/results.md`, `questions/q1/derivation.md` | 当前保留混合模型以维持等速解析关系和等马赫声速计算；后续若做工程级模型，应统一为分层标准大气。 |
| 跨/近音速波阻需要正面说明 | 已列为局限 | `questions/q1/results.md` | 题面未给临界马赫数和波阻参数，主模型不凭空加入波阻；可作为后续灵敏度扩展。 |
| `cT` 数量级风险需要讨论 | 已处理 | `questions/q1/results.md`, `questions/q1/artifacts/tables/sensitivity_summary.csv` | 主结果严格使用题设 `2.8e-4`，另用 `2.8e-5` 做工程合理性对照，不静默替换题设参数。 |
| 等马赫爬升率较小的数学解释需要强化 | 已处理 | `questions/q1/derivation.md`, `questions/q1/results.md` | 已补充 `d ln m/dh=-1/Hrho-L/(T0-Lh)` 的解释，说明声速下降降低动压，使同质量减少下高度增量较小。 |
| q1 README 产物路径与 manifest 不一致 | 已处理 | `questions/q1/README.md`, `questions/q1/manifest.yaml` | README 改为 `questions/q1/artifacts/...`，根目录 `artifacts/q1/data/` 仅保留核心跨文档数据表。 |

## 4. 不适用或暂不实现的建议

| 审查项 | 当前处理 | 理由与风险 |
|---|---|---|
| Literal / Corrected / No-wind 三风场场景 | 部分实现 | 当前 OCR 题面与用户确认均为 `20+0.00003(h-10000)^2 = 20+3e-5(h-10000)^2`，不是 `0.003`；因此“Literal=0.003”不作为本仓库主证据。No-wind 对照已在验证中实现。若后续需要，可新增 `0.003` 异常风场作为反例表。 |
| 固定航程公平油耗对比 | 暂不实现 | q1 题设终止条件为固定终止质量，故总油耗必同为 `10450 kg`。固定航程油耗对比是有价值的补充实验，但会改变比较工况，建议作为 q2 或 q1 扩展表单独实现。 |
| 统一分层标准大气数值模型 | 暂不实现 | 会改变当前等速解析闭合和已有结果数值。当前 q1 作为基线保留原模型，并在局限中说明；若切换，应作为新模型版本重新生成全部图表和证据链。 |
| 波阻扩展模型 | 暂不实现 | 缺少题设参数，直接加入会引入未校准自由参数。建议只在后续做参数化敏感性，不进入 q1 主结论。 |

## 5. 对当前主结论的影响

- q1 主表刷新后，等速策略：`final_time_s=761.916739`，`final_distance_m=200668.442473`，`final_height_m=10637.064671`，`mean_climb_rate_mps=1.492374`。
- 等马赫策略：`final_time_s=811.031777`，`final_distance_m=211331.295605`，`final_height_m=10437.817757`，`mean_climb_rate_mps=1.156327`。
- 固定终止质量下总燃油消耗仍均为 `10450 kg`，该指标不区分策略。
- 空速累计航程分别为 `182860.017 m` 和 `193315.658 m`，风场航程贡献分别为 `17808.425 m` 和 `18015.638 m`，航程差异主要来自飞行时间而非风速差异。
- 审查后可以保留 q1 基线结论，但论文中必须同时写出闭合假设、混合大气模型、未建模波阻、固定终止质量和数值一致性验证局限。
