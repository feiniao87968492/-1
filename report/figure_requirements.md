# q1--q4 正文插图与 GPT-Image2 提示词清单

本文档用于指导论文正文插图生成与插入。根据 `gpt-image-2-style-library`，本文图表统一采用 `infographic-engine` 与 `document-publishing` 风格：白底、少刻度、短标签、蓝橙对比、阈值线清楚、关键数值直接标注。数据型图必须由 CSV 精确绘制，GPT-Image2 提示词只用于统一版式、说明风格和生成非精确示意图，不得让图像模型自行改写数值。

## 总体规范

- 每个问题 3--5 幅图，图随正文论述分散出现，不集中堆在小节末尾。
- 图内中文标签必须短，字号在 PDF 中可读，避免文字压住曲线。
- 数据图统一输出到 `report/figures/`，本轮推荐文件名前缀为 `fig_v2_`。
- 正文中每幅图前先提出需要解释的判断，图后用 1--2 句给出量化解释。
- 不使用 imagegen 直接生成精确数值图；精确图由 `report/scripts/generate_paper_figures_v2.py` 从 CSV 生成。

## 图表总览

| 问题 | 推荐图 | 正文作用 |
|---|---|---|
| q1 | 4 幅 | 解释经验策略闭合、轨迹差异和工程指标差异 |
| q2 | 4 幅 | 解释大气修正、油耗差累积和温差灵敏度 |
| q3 | 6 幅 | 解释无风不可行、最终轨迹、控制量、网格稳定和验证 |
| q4 | 6 幅 | 解释有风节油、轨迹形态、固定燃油航程、β 灵敏度和验证 |

## q1 插图

### q1-1 升力平衡闭合机理

- 文件：`fig_v2_q1_closure_mechanism.pdf`
- 插入位置：问题一“两类巡航爬升策略”公式之后。
- 论证作用：说明两种策略都由升力平衡闭合高度，但等速和等马赫的速度约束不同，导致质量下降时高度曲线分离。
- 数据来源：
  - `artifacts/q1/data/constant_speed_profile.csv`
  - `artifacts/q1/data/constant_mach_profile.csv`
  - 字段：`mass_kg`、`height_m`、`airspeed_mps`、`mach`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine，document-publishing。
用途：数学建模论文中的数据化机制图。
画面：白底科技论文图，横轴“质量 / kg”，纵轴“高度 / m”，两条曲线对比“等速”和“等马赫”，蓝色表示等速，橙色表示等马赫。
信息层级：起点标注 m0=72450 kg，高度 9500 m；终点标注 mf=62000 kg；用短箭头标注“质量下降”“高度上升”。
风格：清爽、留白充足、坐标刻度少、线条粗细适中，中文标签清晰。
约束：不要生成虚构数据，不要遮挡曲线，不要使用 3D、渐变背景、密集网格和装饰图标。
输出：横向论文插图，PDF 矢量图优先。
```

### q1-2 高度--时间轨迹对比

- 文件：`fig_v2_q1_height_time.pdf`
- 插入位置：问题一结果表之后。
- 论证作用：支撑“等速策略终点高度更高、用时更短；等马赫策略飞行时间更长”。
- 数据来源：
  - `artifacts/q1/data/constant_speed_profile.csv`
  - `artifacts/q1/data/constant_mach_profile.csv`
  - 字段：`time_s`、`height_m`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：论文结果证据图。
画面：白底二维折线图，横轴“时间 / s”，纵轴“高度 / m”，蓝色实线“等速”，橙色实线“等马赫”。
重点标注：等速终点高度 10637.065 m，等马赫终点高度 10437.818 m；用轻量标注说明“等速更快爬升”。
风格：科学论文图、少刻度、弱网格、图例放右上角，不遮挡曲线。
约束：不要把图例放在线上，不要出现大段文字，不要把纵轴截断得误导。
```

### q1-3 爬升率剖面对比

- 文件：`fig_v2_q1_climb_rate.pdf`
- 插入位置：紧跟 q1-2 或与 q1-2 分散在结果解释段。
- 论证作用：解释高度差来自爬升率结构，不只是终点数值差。
- 数据来源：
  - `artifacts/q1/data/constant_speed_profile.csv`
  - `artifacts/q1/data/constant_mach_profile.csv`
  - 字段：`time_s`、`climb_rate_mps`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：轨迹机理辅助图。
画面：二维折线图，横轴“时间 / s”，纵轴“爬升率 / (m/s)”，两条曲线蓝橙对比。
重点标注：等速平均爬升率约 1.492 m/s，等马赫爬升率更低且随时间变化。
风格：中文标签清楚，线条不要过细，留白充足。
约束：不要加入飞机照片背景，不要使用复杂纹理，不要把爬升率单位写错。
```

### q1-4 工程指标变化图

- 文件：`fig_v2_q1_metric_comparison.pdf`
- 插入位置：问题一结果分析末尾。
- 论证作用：在“油耗相同”后，突出时间、航程、顺风贡献和平均爬升率才是策略差异。
- 数据来源：
  - `artifacts/q1/data/strategy_comparison.csv`
  - 字段：`final_time_s`、`final_distance_m`、`wind_distance_contribution_m`、`mean_climb_rate_mps`
- GPT-Image2 风格提示词：

```text
模板：document-publishing，infographic-engine。
用途：指标对比图。
画面：横向条形图或哑铃图，四行指标：“时间”“地面航程”“顺风贡献”“平均爬升率”，横轴为“相对变化 / %”。
重点标注：正值表示等马赫高于等速，负值表示等马赫低于等速；0% 参考线清楚。
风格：报告型图表，蓝橙或橙灰配色，标签短而清晰。
约束：不要把不同单位的原始值混在一个坐标轴；不要使用雷达图。
```

## q2 插图

### q2-1 密度修正图

- 文件：`fig_v2_q2_density_correction.pdf`
- 插入位置：问题二“标准大气与常温偏差静力修正”公式之后。
- 论证作用：说明温差修正通过静力平衡影响密度。
- 数据来源：
  - `questions/q2/artifacts/figure_data/atmosphere_path.csv`
  - 字段：`scenario`、`distance_m`、`density_kgm3`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：大气修正模型解释图。
画面：横轴“航程 / km”，纵轴“密度 / (kg/m³)”，标准 ISA 蓝线，+10K 修正橙线。
重点标注：“同一几何路径、同一真空速”，强调密度变化来自静力修正。
风格：白底、弱网格、少刻度、曲线间距清楚。
约束：不要只画温度，不要把 +10K 写成直接油耗结论。
```

### q2-2 声速修正图

- 文件：`fig_v2_q2_sound_speed_correction.pdf`
- 插入位置：与 q2-1 相邻，可在正文中并排插入。
- 论证作用：补充说明温差还改变声速，从而影响马赫数诊断。
- 数据来源：
  - `questions/q2/artifacts/figure_data/atmosphere_path.csv`
  - 字段：`scenario`、`distance_m`、`sound_speed_mps`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：标准大气修正辅助图。
画面：横轴“航程 / km”，纵轴“声速 / (m/s)”，两条曲线清楚对比。
重点标注：+10K 下声速整体较高，进而改变马赫数和气动诊断。
风格：与密度图完全同风格，可并排展示。
约束：不要加入多余变量，不要让图例遮挡曲线。
```

### q2-3 沿程油耗差累积图

- 文件：`fig_v2_q2_fuel_accumulation.pdf`
- 插入位置：问题二标准 ISA 与 +10K 结果表附近。
- 论证作用：解释 `22.744 kg` 差异不是局部突变，而是全程小差异累积。
- 数据来源：
  - `questions/q2/artifacts/figure_data/fuel_rate_path.csv`
  - 字段：`scenario`、`distance_m`、`cumulative_fuel_path_kg`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine，document-publishing。
用途：关键数值来源图。
画面：单条橙色曲线，横轴“航程 / km”，纵轴“累计油耗差 / kg”，终点直接标注“22.744 kg”。
重点标注：曲线平滑上升，说明差异由沿程累积产生。
风格：白底、重点数值用橙色标签，0 线和终点标签清楚。
约束：不要画两个 10400 kg 量级柱子，不要把终点差写成百分比主图。
```

### q2-4 温差灵敏度图

- 文件：`fig_v2_q2_temperature_sensitivity.pdf`
- 插入位置：问题二温差灵敏度分析。
- 论证作用：支撑 `|\Delta T|\leq10K` 内总油耗变化小于 `0.3%`。
- 数据来源：
  - `questions/q2/artifacts/figure_data/temperature_sensitivity.csv`
  - 字段：`temperature_offset_k`、`fuel_delta_vs_standard_pct`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：灵敏度曲线。
画面：横轴“温差 / K”，纵轴“相对 ISA 变化 / %”，点线图，0% 基准线，+10K 标注 0.218%，-10K 标注 -0.276%。
风格：紫色主线，灰色基准线，中文单位清楚。
约束：不要使用过度拟合曲线，不要夸大纵轴范围。
```

## q3 插图

### q3-1 可行性桥接图

- 文件：`fig_v2_q3_feasibility_bridge.pdf`
- 插入位置：问题三固定路径可行性分析附近。
- 论证作用：说明无风固定路径终端质量低于下限，因此必须重新优化。
- 数据来源：
  - `questions/q3/artifacts/tables/baseline_feasibility.csv`
  - `questions/q3/artifacts/tables/no_wind_final_optimal_results.csv`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：模型动机图。
画面：横向条形图，三行：“有风固定路径”“无风固定路径”“无风最终优化”，横轴“终端质量 / kg”，用 62000 kg 阈值线。
重点标注：无风固定路径“缺口 836.526 kg”，无风最终优化“余量 107.186 kg”。
风格：不可行用红色，可行用绿色，阈值线清楚。
约束：不要画总油耗 10k 点图，不要省略 62000 kg 下限。
```

### q3-2 高度走廊图

- 文件：`fig_v2_q3_state_corridor_height.pdf`
- 插入位置：问题三无风最终优化结果表前。
- 论证作用：说明最终轨迹贴近 `12000 m` 高度上界，高度约束接近活跃。
- 数据来源：
  - `questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv`
  - 字段：`distance_m`、`height_m`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：状态轨迹约束图。
画面：横轴“航程 / km”，纵轴“高度 / m”，紫色轨迹线，灰色虚线“12000 m 高度上界”。
重点标注：中段贴近高度上界，终点回到给定高度。
风格：论文级轨迹图，线条清楚，阈值线不抢主线。
约束：不要加入风景或飞机照片背景，不要遮挡高度曲线。
```

### q3-3 质量余量图

- 文件：`fig_v2_q3_state_corridor_mass.pdf`
- 插入位置：与 q3-2 相邻或紧随其后。
- 论证作用：说明最终轨迹终端质量 `62107.186 kg`，仍高于 `62000 kg` 下限。
- 数据来源：
  - `questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv`
  - 字段：`distance_m`、`mass_kg`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：状态约束验证图。
画面：横轴“航程 / km”，纵轴“质量 / kg”，橙色曲线，灰色虚线“62000 kg 下限”，终点标注“62107.186 kg”。
风格：清爽、可读、阈值线清楚。
约束：不要把纵轴格式化成全部 62k 而看不出余量。
```

### q3-4 控制量调度图

- 文件：`fig_v2_q3_control_schedule.pdf`
- 插入位置：问题三最终优化结果表之后。
- 论证作用：展示 reduced-control shooting 得到的推力和航迹角形态，说明解不是黑箱。
- 数据来源：
  - `questions/q3/artifacts/tables/no_wind_final_optimal_trajectory.csv`
  - 字段：`distance_m`、`thrust_n`、`gamma_rad`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：最优控制量剖面图。
画面：横轴“航程 / km”，纵轴“推力 kN / 航迹角缩放”，蓝线表示推力，橙色虚线表示航迹角×10。
重点标注：推力范围 19.634--73.084 kN，航迹角保持小角度。
风格：双变量但不拥挤，图例清楚，单位说明完整。
约束：不要把推力、质量、高度、速度全部塞入同一图。
```

### q3-5 网格稳定性图

- 文件：`fig_v2_q3_grid_stability.pdf`
- 插入位置：问题三网格稳定性诊断表附近。
- 论证作用：说明 `N=61,121,241` 三层网格的燃油结果稳定。
- 数据来源：
  - `questions/q3/artifacts/tables/no_wind_final_optimal_diagnostics.csv`
  - 字段：`final_nodes`、`fuel_used_kg`
- GPT-Image2 风格提示词：

```text
模板：document-publishing。
用途：数值稳定性小图。
画面：横轴“节点数 N”，纵轴“总油耗 / kg”，三个点连线，标注 10342.81 kg 附近稳定。
风格：小而清楚，用于支撑检验段。
约束：不要画旧的空白 Gate 收敛图，不要夸大微小差异。
```

### q3-6 验证仪表图

- 文件：`fig_v2_q3_validation_dashboard.pdf`
- 插入位置：q3 连续验证段。
- 论证作用：证明关键残差低于阈值，验证状态 passed。
- 数据来源：
  - `questions/q3/artifacts/tables/no_wind_final_optimal_validation.csv`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine，document-publishing。
用途：验证残差仪表图。
画面：横向条形图，指标为“速度”“高度”“燃油”“网格”，横轴“log10(残差/阈值)”，0 为阈值线，所有条形位于 0 左侧。
重点标注：passed，速度误差 1.71e-5 m/s，燃油残差 8.58e-5 kg。
风格：绿色通过色，阈值线醒目。
约束：不要使用仪表盘拟物样式，不要生成无法读取的小字。
```

## q4 插图

### q4-1 固定航程燃油对比

- 文件：`fig_v2_q4_strategy_savings.pdf`
- 插入位置：问题四有风最优与等速基线对比表附近。
- 论证作用：直观支撑有风局部优化节省 `563.416 kg`，比例 `5.403%`。
- 数据来源：
  - `questions/q4/artifacts/tables/strategy_comparison.csv`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：策略对比主结果图。
画面：两柱或横向条形图，等速基线 10427.256 kg，有风局部优化 9863.840 kg，中间用箭头标注“节省 563.416 kg / 5.403%”。
风格：蓝色基线，绿色优化，白底，数字大而清楚。
约束：不要把两个柱子都缩写成 10k，必须显示差值标注。
```

### q4-2 高度剖面对比

- 文件：`fig_v2_q4_height_profile_compare.pdf`
- 插入位置：问题四有风最优轨迹形态分析。
- 论证作用：说明有风优化采用“中段较低、末段回到终端高度”的剖面。
- 数据来源：
  - `questions/q4/artifacts/figure_data/height_range_comparison.csv`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：轨迹形态对比图。
画面：横轴“航程 / km”，纵轴“高度 / m”，蓝线等速基线，橙线有风优化。
重点标注：中段高度差，末段终端高度约束。
风格：曲线清晰、图例不遮挡、留白充足。
约束：不要把高度曲线画成场景插画，不要省略坐标轴。
```

### q4-3 速度与推力剖面

- 文件：`fig_v2_q4_control_profile.pdf`
- 插入位置：紧接 q4-2 或同一轨迹形态段。
- 论证作用：展示有风低维 shooting 的控制调度平稳，空速先降后回到终端值。
- 数据来源：
  - `questions/q4/artifacts/tables/wind_optimal_trajectory.csv`
  - 字段：`distance_m`、`airspeed_mps`、`thrust_n`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：有风最优控制剖面图。
画面：横轴“航程 / km”，蓝线为空速，橙色虚线为推力缩放，标注空速约 234--240 m/s，推力约 47.6--47.7 kN。
风格：双变量简洁图，图例和单位必须清楚。
约束：不要生成密集多轴图，不要让文字覆盖曲线。
```

### q4-4 固定燃油航程下界图

- 文件：`fig_v2_q4_fixed_fuel_range.pdf`
- 插入位置：问题四固定燃油口径下的航程估计。
- 论证作用：支撑 `201168.189 m` 是当前局部网格支持的可达航程下界。
- 数据来源：
  - `questions/q4/artifacts/tables/fixed_fuel_range_trials.csv`
  - `questions/q4/artifacts/tables/fixed_fuel_range.csv`
- GPT-Image2 风格提示词：

```text
模板：document-publishing。
用途：固定燃油航程估计图。
画面：横向条形图，三行航程因子 1.00×、1.03×、1.06×，横轴“试验航程 / km”，1.06× 标注“201.168 km，仍预算内”。
风格：绿色表示通过预算检查，标题说明“下界估计，不是最大航程证明”。
约束：不要写成最大航程，不要省略下界口径。
```

### q4-5 β 灵敏度响应

- 文件：`fig_v2_q4_beta_sensitivity.pdf`
- 插入位置：问题四 β 灵敏度段。
- 论证作用：展示 β 从 0.8 到 1.2 时燃油变化不超过 `14.116 kg`，且只支持局部可行敏感性。
- 数据来源：
  - `questions/q4/artifacts/tables/beta_sensitivity.csv`
- GPT-Image2 风格提示词：

```text
模板：infographic-engine。
用途：局部灵敏度曲线。
画面：横轴“β 因子”，纵轴“相对标称燃油变化 / kg”，紫色点线，0 kg 基准线。
重点标注：0.8 倍为 -14.116 kg，1.2 倍为 +6.230 kg；角落注明“局部可行响应”。
风格：克制、科学、避免夸大。
约束：不要写成严格最优敏感性，不要把 failed optimizer 状态隐藏成强结论。
```

### q4-6 有风优化验证卡

- 文件：`fig_v2_q4_validation_card.pdf`
- 插入位置：模型检验中“问题四有风优化检验”。
- 论证作用：展示终端高度、速度、燃油恒等式和路径约束均通过验证。
- 数据来源：
  - `questions/q4/artifacts/tables/wind_optimal_results.csv`
- GPT-Image2 风格提示词：

```text
模板：document-publishing，infographic-engine。
用途：验证摘要图。
画面：横向条形图，指标“高度”“速度”“燃油”“约束”，横轴 log10(残差/阈值)，0 为阈值线，所有条形在通过侧。
重点标注：高度误差 6.31e-7 m，速度误差 1.51e-8 m/s，燃油残差 0.0316 kg，validation_status=passed。
风格：绿色通过、灰色阈值线、清晰短标签。
约束：不要使用复杂仪表盘，不要生成不可读小字。
```

## 生成与插入建议

1. 先运行：

```powershell
& 'C:\Users\miwus\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\report\scripts\generate_paper_figures_v2.py
```

2. 正文插入时，不必全部使用 20 张图。优先保留每问 3 张核心图：
   - q1：闭合机理、高度时间、指标变化；
   - q2：密度修正、油耗累积、温差灵敏度；
   - q3：可行性桥接、状态走廊、验证仪表；
   - q4：燃油对比、高度剖面、固定燃油航程或 β 灵敏度。
3. 若版面允许，再加入 q3 控制量、q4 控制剖面、q4 验证卡等辅助图。
4. 所有图后必须有一句量化解释，不允许图孤立出现。
