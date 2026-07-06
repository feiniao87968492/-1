# q2 review1 对照审计

来源：`questions/q2/review1.md`

## 处理结论

review1 的核心判断合理。旧版 q2 将“只改温度、压力仍用 ISA”的实现称为完整非标准大气修正，并错误表述声速会改变固定真空速燃油惩罚项。现已按静力平衡压力修正、路径域积分和多温差灵敏度重算全部 q2 结果。

## 逐项处理

| review 项 | 处理状态 | 修改位置 | 说明 |
|---|---|---|---|
| P0：非标准大气应同步修正压力 | resolved | `questions/q2/scripts/fuel_path_model.py` | 新增 `corrected_pressure_pa`，使用 `p_delta=p0[(T0+DeltaT-Lh)/(T0+DeltaT)]^{g/(RL)}` |
| P0：删除声速改变燃油惩罚项的错误表述 | resolved | `questions/q2/approach.md`; `questions/q2/results.md` | 明确声速在当前等真空速模型中只作为马赫诊断量 |
| P0：显式写出路径积分 | resolved | `questions/q2/approach.md`; `questions/q2/scripts/fuel_path_model.py` | 写出 `J=∫q_f/V_g dx`，剖面保存 `fuel_per_meter_kgpm` 和累计积分列 |
| P0：不要把旧模型称为完整修正 | resolved | `questions/q2/experiments.md`; `questions/q2/results.md` | 旧固定 ISA 压力方案列为失败实验并废弃 |
| P1：不能只用 `+10 K` 得出忽略条件 | resolved | `artifacts/q2/data/q2_temperature_sensitivity.csv` | 计算 `{-10,-5,-2,0,2,5,10} K` |
| P1：增加静力平衡、积分一致、步长敏感性等验证 | resolved | `questions/q2/scripts/validate.py` | 新增静力残差、`DeltaT=0` 收敛、时间/路径积分、步长、正负温差、小角度、推力和平滑性检查 |
| P1/P2：补充大气参数和温差敏感性图 | resolved | `questions/q2/scripts/visualize.py` | 新增 `atmosphere_path.png` 和 `temperature_sensitivity.png` |
| P1：加入等马赫对照使声速直接进入动力学 | deferred | `questions/q2/results.md` 局限 | 当前 q2 保持固定真空速主模型，等马赫/波阻作为后续扩展，不混入本次基线修复 |

## 重算后的关键变化

旧版固定 ISA 压力简化模型给出 `+10 K` 油耗减少约 `129.665 kg`。静力平衡修正后，`+10 K` 场景总油耗为 `11039.346 kg`，相对标准 ISA `11004.536 kg` 增加 `34.810 kg`，相对变化 `0.316%`。旧数值不再作为支持性结论使用。
