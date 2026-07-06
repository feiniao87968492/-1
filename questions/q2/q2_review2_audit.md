# q2 review2 对照审计

来源：`questions/q2/review2.md`

## 处理结论

review2 的核心判断成立。上一版 q2 虽然修复了静力平衡压力和路径积分，但仍把 q1 指数密度模型下的固定 `CL_ref` 直接带入 ISA，导致反算初始高度偏离题设 `9500 m`，轨迹越过 11 km，并在完整 q1 航程下突破题设终止质量。现已改为固定 q1 等速几何路径和速度路径，在每种大气条件下重新计算 `CL(x)`、阻力和油耗，并用共同可行航程保证所有温差场景 `m(tf)>=62000 kg`。

## 逐项处理

| review 项 | 处理状态 | 修改位置 | 说明 |
|---|---|---|---|
| 初始高度被静默改变 | resolved | `questions/q2/scripts/fuel_path_model.py`; `validate.py` | 固定 q1 等速路径，新增 `initial_state_match`，所有场景 `h(0)=9500 m`、`V(0)=240 m/s`、`m(0)=72450 kg` |
| 单层对流层公式被用于 11 km 以上 | resolved | `fuel_path_model.py`; `validate.py` | 大气函数支持 11 km 以上等温层；当前共同航程路径最高低于 11 km，并由 `atmosphere_layer_valid` 检查 |
| q1 航程下终止质量约束被突破 | resolved | `fuel_path_model.py`; `validate.py` | 共同航程取各温差场景达到 `62000 kg` 的最短航程，新增 `terminal_mass_constraint` |
| 推荐方案 B：固定几何路径 | adopted | `fuel_path_model.py`; `approach.md` | 使用 `artifacts/q1/data/constant_speed_profile.csv` 的 `h_ref(x),V_ref(x)`，各场景重算 `CL(x)` |
| 路径积分、静力压力、声速说明、多温差灵敏度可保留 | retained | `approach.md`; `results.md` | 保留并刷新数值、图表和证据链 |

## 重算后的关键变化

上一版 `+10 K` 静力修正结果基于固定 `CL_ref` 反算高度，标准 ISA 油耗为 `11004.536 kg`，`+10 K` 为 `11039.346 kg`。修复后采用共同可行航程 `189781.310 m`：标准 ISA 油耗为 `10427.256 kg`，`+10 K` 为 `10450.000 kg`，相对增加 `22.744 kg`，即 `0.218%`。旧数值不再作为支持性结论使用。
