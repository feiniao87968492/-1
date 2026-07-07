# 风险登记表

| 风险 ID | 风险 | 概率 | 影响 | 触发信号 | 缓解措施 | 负责人 / 小问 | 状态 |
|---|---|---|---|---|---|---|---|
| R001 | 题意解释错误 | 中 | 高 | 输出与题面不一致 | 先完成问题重述并记录歧义 | 全项目 | open |
| R002 | 数据口径不一致 | 中 | 高 | 单位或时间范围冲突 | 数据字典与量纲审计 | 全项目 | open |
| R003 | 模型过拟合或不稳健 | 中 | 高 | 验证波动大 | 基线、交叉验证和灵敏度分析 | 各小问 | open |
| R004 | q1 必需题面入口缺失 | 中 | 高 | `question.md`、`questions/q1/brief.md` 不存在 | 已按用户选择 C 从 OCR 文件补齐题面入口 | q1 | mitigated |
| R005 | q1 风场公式口径冲突 | 中 | 中 | OCR 题面为 `3e-5`，`overview.md` 早期建议为 `3e-6` | 已按用户指定采用 `20+3e-5(h-10000)^2`，最终审计中说明差异 | q1 | mitigated |
| R006 | q1 固定终止质量导致总油耗指标无区分度 | 高 | 中 | 两策略总油耗均为 10450 kg | 将总油耗报告为题设固定值，比较航程/时间/高度/爬升率；固定航程油耗列为扩展实验 | q1 | mitigated |
| R007 | `tasks/task2.md` 为空导致 q2 任务入口缺失 | 高 | 中 | `tasks/task2.md` 文件大小为 0 | 采用 `question.md` 中问题 2 作为权威题面，并在 q2 文档中记录该口径 | q2 | mitigated |
| R008 | q2 温度偏差场景缺少真实气象数据 | 中 | 中 | 未提供实测温度剖面 | 采用多组常温偏差静力平衡修正做灵敏度，结果不外推为真实天气结论 | q2 | open |
| R009 | q2 非标准大气压力处理不满足静力平衡 | 中 | 高 | review 指出只改温度、压力仍用 ISA | 已废弃固定 ISA 压力简化模型，新增静力平衡残差验证 | q2 | mitigated |
| R010 | q2 沿用 q1 指数大气 `CL_ref` 导致初始状态偏移 | 中 | 高 | review2 指出 ISA 反算初始高度约 11.68 km 而非 9.5 km | 已改为固定 q1 几何路径并重算 `CL(x)`，新增初始状态和大气层门禁 | q2 | mitigated |
| R011 | q2 固定完整 q1 航程突破终止质量下限 | 中 | 高 | ISA 或温差场景终点质量低于 `62000 kg` | 共同航程取所有温差场景达到终止质量的最短航程，新增终点质量门禁 | q2 | mitigated |
| R012 | q3 固定终止质量导致优化目标退化 | 高 | 高 | `m(tf)=62000 kg` 且目标为 `m0-m(tf)` | q3 主问题改为固定航程并最大化终端质量 | q3 | mitigated |
| R013 | q3 终端机械能自由导致虚假省油 | 中 | 高 | 最优解降低终端高度或速度 | 固定终端高度和速度，终端能量约束仅作为扩展 | q3 | mitigated |
| R014 | q3 飞行包线边界来自仿真假设 | 高 | 中 | 题面未给推力/马赫/控制变化率边界 | 边界写入配置并计划敏感性分析 | q3 | open |
| R015 | q3 q2 有风基线不能作为无风可行初值 | 高 | 高 | 固定 q1 路径无风重算终端质量低于 `62000 kg` | 新增 `precheck.py` 和 `baseline_feasibility.csv`；正式求解前需重构无风可行轨迹、缩短航程或确认放宽质量约束 | q3 | open |
| R016 | q3 控制变化率约束与 PMP 简化条件不一致 | 中 | 中 | 使用 `|dot T|`、`|dot gamma|` 同时仍检查 `partial H/partial u=0` | 文档区分无变化率约束的一阶条件和扩展状态严格处理 | q3 | mitigated |
| R017 | q3 自由终端时间和零推力模型可能产生非运营解 | 中 | 高 | 最优解大幅延长 `tf` 或频繁贴近 `T=0` | 计划报告时间约束对照，并做怠速推力/基础油耗敏感性 | q3 | open |
| R018 | q3 低维可行性 Gate 被误读为全局可行性结论 | 中 | 高 | `s*>0` 被写成“无风不可行”或 `s*≈0` 被写成“已最优” | `q3_review2_audit.md` 和证据链明确其只是一阶 Gate；正式结论需完整 collocation、多初值和网格敏感性 | q3 | open |
| R019 | q3 Gate 1 结果可能由高度上界驱动 | 高 | 中 | Gate 1 轨迹 `max h` 几乎等于 `h_max=12000 m` | 在完整 collocation Gate 2 中报告活跃约束，并优先做 `h_max` 敏感性 | q3 | open |
| R020 | q3 11 km 大气层非光滑影响梯度型配点诊断 | 高 | 中 | Gate 1 已两次穿越 11 km，且达到 12 km | Gate 2 前采用 10950-11050 m C1 平滑过渡，或单独报告 h_max<=10950 m 对流层内版本 | q3 | open |
| R021 | q3 航程域 KKT 被误当时间域 PMP 验证 | 中 | 中 | 直接把航程域缺陷乘子代入时间域 Hamiltonian | 先报告航程域 Hamiltonian/KKT；时间域映射未推导前不声称时间域 Hamiltonian 验证通过 | q3 | open |
| R022 | q3 Gate 2 dry-run 被误读为完整 collocation 可行解 | 中 | 高 | `no_wind_collocation_gate.csv` 被直接写入最终结果 | dry-run 表使用 `dry_run_not_optimized` 状态；证据链明确其只验证投影和诊断链，完整 NLP 优化后才可判定 Gate 2 | q3 | open |

| R023 | q3 warm-start hmax 诊断被误读为优化敏感性 | 中 | 高 | `warm_start_hmax_diagnostic.csv` 被写成 `s*(h_max)` 或 optimized sensitivity | 表名、表内状态、review5 审计和证据链均标注 `warm_start_only_not_optimized`；正式优化敏感性需另存 `optimized_hmax_sensitivity.csv` | q3 | open |
