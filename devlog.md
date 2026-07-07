# Development Log

## 使用规则

仅记录有决策价值的工作节点。每次记录包含目标、发现、决策、产物、未解决问题和下一步。

---

## 2026-07-06T15:17:28+08:00 — 仓库初始化

- **目标**：建立 实训1 的可复现建模仓库。
- **完成**：初始化项目结构、4 个小问模板、证据链、图表登记表和审计脚本。
- **关键发现**：题面、数据和各小问具体目标尚待填写。
- **决策**：采用项目级公共文档 + 小问级独立流水线结构。
- **产物**：见仓库初始提交。
- **未解决问题**：题意歧义、数据来源、评价指标、模型路线。
- **下一步**：完成 `docs/problem_statement.md` 和各小问 `approach.md`。

## 2026-07-06T18:30:00+08:00 — q1 代码前题意阻断

- **目标**：按 `tasks/task1.txt` 启动第一问，并在正式代码书写前完成阻断确认。
- **完成**：读取仓库规则、q1 任务、`tasks/overview.md`、q1 模板、证据链和 devlog；写入 `questions/q1/review.md`、`modeling_state.yaml`、`task_plan.md`、`findings.md`、`progress.md`。
- **关键发现**：`question.md` 与 `questions/q1/brief.md` 缺失；q1 存在水平飞行/巡航爬升、控制变量定义、风场量级、固定终止质量等关键歧义。
- **决策**：不进入正式实现代码；先请求用户确认是否采用 `tasks/overview.md` 的统一建模口径。
- **产物**：`questions/q1/review.md`、`modeling_state.yaml`、`data/interactions/user_decisions.yaml`。
- **未解决问题**：是否采用缩放风场；是否以 OCR 文件作为题面来源；是否按 `overview.md` 的 `C_L=C_L*` 闭合条件实现。
- **下一步**：用户确认后，进入 q1 推导与实现。

## 2026-07-06T18:34:27+08:00 — q1 补齐题面入口

- **目标**：按用户选择 C，先补充 `question.md` 和 `questions/q1/brief.md` 后再审题。
- **完成**：基于 `cumcm_gmcm2026_qinsen_Model1.pdf_by_PaddleOCR-VL-1.6.md` 创建 `question.md` 与 `questions/q1/brief.md`，并更新确认记录。
- **关键发现**：补齐题面后，控制变量定义、水平飞行与巡航爬升冲突、固定终止质量和风场量级异常仍然存在。
- **决策**：继续保持代码前阻断，创建新的确认项 `confirm_stage1_q1_reaudit_001`。
- **产物**：`question.md`、`questions/q1/brief.md`、更新后的 `questions/q1/review.md`。
- **未解决问题**：是否采用 `tasks/overview.md` 的统一口径进入正式推导与代码实现。
- **下一步**：等待用户确认 A/B/C/D。

## 2026-07-06T18:42:43+08:00 — q1 风场口径修订

- **目标**：记录用户对风速大小的统一修订。
- **完成**：将 q1 主风场公式更新为 `W(h)=20+3e-5(h-10000)^2`，并在审题、假设、决策、风险和进度文件中登记。
- **关键发现**：该口径与 OCR 题面中的 `0.00003` 一致，但不同于 `tasks/overview.md` 中的 `3e-6` 建议，应在最终审计中明确列为用户修订/确认。
- **决策**：后续 q1 主模型、代码和图表使用 `3e-5` 风场系数；`overview.md` 的 `3e-6` 建议不作为主计算口径。
- **产物**：更新 `questions/q1/review.md`、`questions/q1/brief.md`、`docs/assumptions.md`、`docs/decision_log.md`、`docs/risk_register.md`。
- **未解决问题**：是否接受补齐题面、修订风场与 `overview.md` 其余统一口径并进入代码实现。
- **下一步**：等待用户确认进入实现。

## 2026-07-06T18:47:48+08:00 — q1 进入实现

- **目标**：处理用户 A 确认，进入 q1 推导、代码与实验阶段。
- **完成**：写入 `decision_stage1_003`，解除代码前阻断。
- **关键发现**：实现必须保留题意歧义说明，不得预设等马赫爬升率一定更大。
- **决策**：按 TDD 先写验收测试，再实现模型脚本。
- **产物**：更新 `modeling_state.yaml`、`data/interactions/user_decisions.yaml`、`questions/q1/manifest.yaml`。
- **未解决问题**：待数值验证确定两策略指标和爬升率差异。
- **下一步**：写 q1 行为测试并执行红灯测试。

## 2026-07-06T19:05:00+08:00 — q1 完成与审计

- **目标**：完成 `tasks/task1.txt` 对第一问的建模、推导、代码、数值实验、图表、验证和证据链，并对照 `tasks/overview.md` 审计。
- **完成**：实现 q1 拆分脚本，生成两策略剖面、策略对比表、验证/灵敏度表和五张图；补全 `approach.md`、`derivation.md`、`experiments.md`、`evidence.md`、`results.md`、`overview_audit.md`。
- **关键发现**：固定终止质量使两策略总油耗均为 `10450 kg`；本模型下等速平均爬升率高于等马赫，不支持预设“等马赫更大”。
- **决策**：最终结论按数值验证写入，不为迎合题面修改结果；风场使用用户确认 `3e-5` 系数。
- **产物**：`artifacts/q1/data/*.csv`、`questions/q1/artifacts/figures/*.png`、`questions/q1/artifacts/figure_data/*`、`docs/evidence_chain.csv`、`docs/figure_table_registry.csv`。
- **未解决问题**：q2-q4 仍为模板状态，仓库检查仅对这些小问给出 warning。
- **下一步**：若继续后续小问，应按同一证据链流程处理。

## 2026-07-06T19:35:00+08:00 — q1 review 再审计与修正

- **目标**：按用户要求对照 `tasks/q1_review.md` 审核 q1，并修复 reviewer 指出的报告指标和验证缺口。
- **完成**：修正平均爬升率/平均地速为端点差除以总时间；将步长敏感性改为检查 `final_time_s`、`final_distance_m`、`mean_climb_rate_mps`；将 `beta` 灵敏度扰动改为读取 `configs/default.yaml` 的 `[-20%, -10%, +10%, +20%]`；补充 `questions/q1/q1_review_audit.md`。
- **关键发现**：旧文档中等马赫平均爬升率仍保留为 `1.157443 m/s`，已按新输出更新为 `1.156327 m/s`；`tasks/q1_review.md` 的 Literal 风场建议基于 `0.003` 前提，而当前 OCR 与用户确认口径为 `0.00003=3e-5`。
- **决策**：保留 q1 主模型为基线模型，不新增未校准波阻或分层标准大气模型；固定航程油耗作为后续扩展，不混入固定终止质量主工况。
- **产物**：更新 `questions/q1/approach.md`、`derivation.md`、`experiments.md`、`evidence.md`、`results.md`、`questions/q1/q1_review_audit.md`、`docs/evidence_chain.csv`、`docs/figure_table_registry.csv`。
- **未解决问题**：若论文需要“固定航程公平油耗”或“0.003 异常风场反例”，需新增独立扩展实验。
- **下一步**：运行完整测试、q1 pipeline、q1 validation 和仓库自检。

## 2026-07-06T20:05:00+08:00 — q1 review (2) 收尾修正

- **目标**：按 `tasks/q1_review (2).md` 修复 q1 文档冲突、控制量表述、验证自证性和航程归因问题。
- **完成**：将 `questions/q1/review.md` 状态改为 `RESOLVED`；统一将 `gamma` 表述为轨迹变量；新增小航迹角、隐式 ODE 分母、推力正性、等速解析终点和等马赫约束验证；策略对比表新增 `air_distance_m` 与 `wind_distance_contribution_m`；更新结果、证据、推导、实验和审计记录。
- **关键发现**：等马赫地面航程更大主要来自飞行时间更长，风场贡献差异仅约 `207 m`。
- **决策**：保留 q1-baseline 主模型，不更换混合大气和未校准波阻模型；将新增诊断作为基线冻结前的质量门控。
- **产物**：更新 `artifacts/q1/data/strategy_comparison.csv`、`questions/q1/artifacts/tables/validation_summary.csv`、`questions/q1/q1_review_audit.md`、`questions/q1/results.md`、`questions/q1/derivation.md`。
- **未解决问题**：固定航程公平油耗、统一标准大气和波阻扩展仍作为后续模型版本处理。
- **下一步**：运行完整测试、q1 pipeline、q1 validation、仓库自检并提交推送。

## 2026-07-06T20:45:00+08:00 — q2 固定航程油耗积分

- **目标**：处理 `tasks/task2.md` 指向的第二问，建立标准大气与温度偏差下的巡航全过程油耗路径积分模型。
- **完成**：确认 `tasks/task2.md` 为 0 字节，改用 `question.md` 的问题 2 作为权威题面；实现 q2 固定航程燃油积分、验证和可视化；生成标准 ISA 与 `+10 K` 温度修正结果。
- **关键发现**：固定 q1 等速参考航程 `200668.442 m` 下，标准 ISA 总油耗为 `11004.536 kg`，旧版 `+10 K` 固定 ISA 压力简化模型给出 `10874.871 kg`；该温度修正口径已在后续 review 中被废弃。
- **决策**：q2 使用固定航程而非固定终止质量；温度偏差处理的旧版实现待 review 后修正。
- **产物**：`artifacts/q2/data/q2_fuel_summary.csv`、q2 两个剖面 CSV、`questions/q2/artifacts/tables/*.csv`、`questions/q2/artifacts/figures/fuel_rate_path.png`、同名生图数据和元数据。
- **未解决问题**：真实气象温度剖面未提供；当前 `+10 K` 为示例场景。
- **下一步**：运行完整测试、q2 pipeline、q2 validation、仓库自检并提交推送。

## 2026-07-06T21:20:00+08:00 — q2 review1 修正

- **目标**：按 `questions/q2/review1.md` 修复第二问非标准大气、声速解释、路径积分和温差灵敏度证据缺口。
- **完成**：将温度偏差压力改为满足静力平衡的常偏差公式；新增路径域积分输出和时间/路径积分一致性验证；计算 `{-10,-5,-2,0,2,5,10} K` 温差灵敏度；补充静力残差、步长敏感性、正负温差响应、小角度、推力和平滑性检查；新增大气路径图、温差敏感性图和 `q2_review_audit.md`。
- **关键发现**：旧版固定 ISA 压力简化模型的 `+10 K` 减油结论不成立。静力修正后，标准 ISA 总油耗为 `11004.536 kg`，`+10 K` 为 `11039.346 kg`，增加 `34.810 kg`，相对 `0.316%`。
- **决策**：保留固定真空速、固定 `CL_ref` 作为 q2 主操作规律；声速在当前模型中只作为马赫诊断量，不写成燃油惩罚项驱动因素；等马赫、波阻或马赫相关发动机效率作为后续扩展。
- **产物**：更新 `questions/q2/scripts/*.py`、`artifacts/q2/data/*.csv`、`questions/q2/artifacts/figures/*.png`、`questions/q2/approach.md`、`results.md`、`experiments.md`、`evidence.md`、`docs/evidence_chain.csv`、`docs/figure_table_registry.csv`。
- **未解决问题**：真实非标准温度剖面、固定几何路径对照和等马赫声速直接作用模型尚未加入。
- **下一步**：运行完整测试、q2 pipeline、q2 validation、仓库自检并提交推送。

## 2026-07-06T22:20:00+08:00 — q2 review2 修正

- **目标**：按 `questions/q2/review2.md` 修复 q2 初始状态、大气层适用范围和终点质量约束问题。
- **完成**：废弃“q1 指数大气固定 `CL_ref` 在 ISA 中反算高度”的接口；改为固定 q1 等速几何路径和速度路径，在各大气场景中重算 `CL(x)`、阻力和油耗；共同航程取所有温差场景到达 `62000 kg` 的最短航程；新增 `initial_state_match`、`atmosphere_layer_valid` 和 `terminal_mass_constraint` 验证门禁；补充 `q2_review2_audit.md`。
- **关键发现**：修正后共同可行航程为 `189781.310 m`；标准 ISA 总油耗为 `10427.256 kg`，`+10 K` 为 `10450.000 kg`，增加 `22.744 kg`，相对 `0.218%`。
- **决策**：q2 主模型采用固定几何路径口径，以隔离大气参数变化对 `CL(x)`、诱导阻力和油耗的影响；完整 q1 航程不再作为 q2 主比较航程，因为会突破终止质量下限。
- **产物**：更新 `questions/q2/scripts/*.py`、`artifacts/q2/data/*.csv`、`questions/q2/artifacts/*`、`approach.md`、`results.md`、`experiments.md`、`evidence.md`、`q2_review2_audit.md`、全局证据链与登记表。
- **未解决问题**：真实非标准温度剖面、等马赫/波阻/马赫相关发动机效率仍作为后续扩展。
- **下一步**：运行完整测试、q2 pipeline、q2 validation、仓库自检并提交推送。

## 2026-07-06T22:45:00+08:00 — q3 最优控制建模设计

- **目标**：按 `tasks/task3.md` 完成第三问题意审计、优化问题定义、必要条件推导和数值求解方案设计，不生成正式最优数值。
- **完成**：补齐 `questions/q3/brief.md`、`review.md`、`approach.md`、`derivation.md`、`experiments.md`、`evidence.md`、`results.md`、`manifest.yaml`；在 `configs/default.yaml` 增加 q3 优化边界假设；更新全局问题拆解、证据链、图表登记、决策和风险。
- **关键发现**：若固定 `m(tf)=62000 kg`，总油耗目标退化为常数；若终端高度/速度自由，可能通过降低终端机械能虚假省油。
- **决策**：q3 采用固定航程 `Xf=189781.310 m`、固定终端高度 `10577.124 m`、固定终端速度 `240 m/s`、终端质量自由的最优控制口径；主求解路线为直接配点，PMP 用于必要条件和诊断。
- **产物**：q3 全套设计文档和配置约束段；本轮不生成最优轨迹、最优油耗或论文级图表。
- **未解决问题**：正式 collocation 求解脚本、无风/有风最优结果、网格敏感性、多初值验证和 Hamiltonian 诊断尚未实现。
- **下一步**：第二轮实现 q3 求解脚本，先无风后有风，并以 q2 路径作为初值。

## 2026-07-07 q3 review1 预检查修订

- **目标**：处理 `questions/q3/review1.md` 指出的求解器前门槛，尤其是 q2 有风基线是否可作为无风 q3 可行初值。
- **完成**：新增 `questions/q3/scripts/precheck.py`、`tests/test_q3_precheck.py` 和 `questions/q3/q3_review1_audit.md`；生成 `questions/q3/artifacts/tables/baseline_feasibility.csv`；更新 q3 `approach.md`、`derivation.md`、`experiments.md`、`results.md`、`evidence.md`、`review.md`、`README.md`、`manifest.yaml` 以及全局证据链、图表登记、决策和风险。
- **关键发现**：配置风场固定路径终端质量 `62022.744 kg`，仍满足 `m>=62000 kg`；无风固定同一路径终端质量 `61163.474 kg`，违反硬质量约束。
- **决策**：q2 有风剖面不能直接作为无风优化可行初值；正式 collocation 求解器实现前，必须重构无风可行轨迹、缩短航程或确认调整质量约束口径。
- **产物**：`baseline_feasibility.csv` 和 q3 review1 对照审计；本轮仍不生成第三问最优轨迹或最优油耗。
- **验证**：`python -m pytest tests\test_q3_precheck.py -q` 已通过。
- **下一步**：围绕无风可行初值/航程/质量硬约束做确认后，再进入 q3 正式求解器实现。
