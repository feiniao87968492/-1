# q3 review7 对照审计

来源：`questions/q3/review7.md`

## 结论

本轮只补充 Gate 2 readiness 级别的可验证诊断，不实现非 dry-run collocation NLP，也不生成正式最优油耗或最优轨迹。

## 处理项

| Review 意见 | 处理 | 证据 | 状态 |
|---|---|---|---|
| 固定推力诊断只能证明 `rho -> D -> dV/dx`，还需证明 `rho -> D -> T_required -> dm/dx` | 在固定 `h,V,m,gamma,dV/dx` 下新增所需推力和对应质量率诊断 | `questions/q3/artifacts/tables/atmosphere_coupling_diagnostics.csv` | resolved |
| 有限差分静力残差需明确为无量纲，并检查步长敏感性 | 将数值静力残差封装为无量纲相对残差，输出 `0.1,0.5,1,2,5 m` 中心差分步长结果 | `questions/q3/artifacts/tables/atmosphere_smoothing_diagnostics.csv` | resolved |
| 正式 NLP 不能只报告配点缺陷，还需独立 ODE 重积分诊断 | 在配置中冻结正式 Gate 2 必报字段：`reintegration_state_error_inf`、终端质量/高度/速度误差 | `configs/default.yaml` | design_resolved |
| 梯形法没有独立中点状态，需说明中点约束定义 | 配置和方案中明确当前为线性中点审计加事后重构检查；若节点间越界，再升级 Hermite-Simpson 或网格细化 | `configs/default.yaml`; `questions/q3/approach.md` | design_resolved |
| 词典序第二阶段不能用质量松弛容差牺牲硬终端质量约束 | 配置冻结第二阶段策略为数值容差下执行硬终端质量约束；若第一阶段 `s_min=0`，不得重新放开到 `s<=1e-3 kg` | `configs/default.yaml`; `questions/q3/approach.md` | design_resolved |
| Q3-C01 至 Q3-C03 可作为理论/设计主张标记 supported | 已把 q3 本地证据和全局证据链状态改为 `supported`，但保留“尚未数值求解”的局限 | `questions/q3/evidence.md`; `docs/evidence_chain.csv` | resolved |

## 新增关键数值

固定状态点采用 `h=11000 m, V=235 m/s, m=67000 kg, gamma=0`，并固定目标速度梯度 `dV/dx=5.0e-4 1/m`：

- C1 相对分层 ISA 的所需推力差：`-2.843277 N`；
- C1 相对分层 ISA 的所需推力质量率差：`3.387735e-06 kg/m`；
- 固定推力质量率差仍为 `0`，这是质量方程结构所致。

无量纲数值静力残差中心差分步长敏感性：

| 步长 m | 最大无量纲残差 |
|---:|---:|
| 0.1 | 4.750640e-10 |
| 0.5 | 1.194341e-08 |
| 1.0 | 4.777402e-08 |
| 2.0 | 1.910967e-07 |
| 5.0 | 1.194352e-06 |

## 边界

这些证据只证明 C1 大气和燃油链路在固定状态诊断中连通，并提高正式 Gate 2 的验证门槛。它们不支持 `s*(h_max)`、非 dry-run 可行性、最优轨迹或最优油耗结论。
