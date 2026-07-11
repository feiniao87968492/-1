# 附录

## 附录 A 问题一核心推导

问题一采用小航迹角准稳态巡航爬升模型。基本方程为

```text
dx/dt = V + W(h)
L = 0.5 rho(h) V^2 S CL ≈ mg
CD = CD0 + k CL^2
D = 0.5 rho(h) V^2 S CD
T = D + m dV/dt + (mg/V) dh/dt
dm/dt = -cT T [1 + beta (V - Vopt)^2]
```

为闭合等速和等马赫数巡航爬升策略，采用

```text
CL = CL_ref = 2 m0 g / [rho(h0) V0^2 S]
```

由题设初始状态得到 `CL_ref=0.658914`。两类策略均可写成 `h=h(m)`、`V=V(m)`，从而化为一维质量方程

```text
dm/dt = - cT Phi(V) D / [1 + cT Phi(V) A(m)]
```

其中

```text
A(m)=m dV/dm + (mg/V) dh/dm
Phi(V)=1+beta(V-Vopt)^2
```

## 附录 B 问题一代码与复现命令

问题一正式入口如下：

```bash
python questions/q1/scripts/pipeline.py --config configs/default.yaml
python questions/q1/scripts/validate.py --config configs/default.yaml
```

主要脚本：

| 文件 | 说明 |
|---|---|
| `questions/q1/scripts/aircraft_model.py` | 气动、阻力、燃油消耗和物理量计算 |
| `questions/q1/scripts/atmosphere.py` | 指数密度与标准声速计算 |
| `questions/q1/scripts/simulate.py` | 两类策略的数值积分与指标计算 |
| `questions/q1/scripts/pipeline.py` | 生成策略剖面和核心结果表 |
| `questions/q1/scripts/validate.py` | 生成验证表和灵敏度表 |
| `questions/q1/scripts/visualize.py` | 生成论文级图表与生图数据 |

## 附录 C 支撑材料清单

| 文件或目录 | 说明 |
|---|---|
| `cumcm_gmcm2026_qinsen_Model1.pdf_by_PaddleOCR-VL-1.6.md` | 赛题 OCR 文本 |
| `question.md` | 本项目整理后的题面入口 |
| `configs/default.yaml` | 全局参数和验证配置 |
| `artifacts/q1/data/strategy_comparison.csv` | 问题一两策略核心指标表 |
| `artifacts/q1/data/constant_speed_profile.csv` | 等速策略完整剖面 |
| `artifacts/q1/data/constant_mach_profile.csv` | 等马赫策略完整剖面 |
| `questions/q1/artifacts/tables/validation_summary.csv` | 问题一验证结果 |
| `questions/q1/artifacts/tables/sensitivity_summary.csv` | 问题一灵敏度结果 |
| `questions/q1/artifacts/figures/` | 问题一论文图 |
| `questions/q1/artifacts/figure_data/` | 问题一生图数据与元数据 |

## 附录 D AI 工具使用详情

1. 所用 AI 工具的名称及版本：Codex，GPT-5，OpenAI，2026-07-06。
2. 使用 AI 工具的具体目的与环节：辅助整理题面、检查模型文档证据链、撰写论文框架和问题一正文草稿。
3. 关键交互记录：用户要求依据题目与已完成的问题一结果撰写论文全框架和问题一正文；AI 读取本地赛题、Q1 结果、验证表和写作规则后生成草稿。
4. 对 AI 生成内容的采纳情况与人工修改情况：本文档为待人工复核草稿；核心模型、数值结果和验证结论均引用本地可复现脚本与结果文件，后续需由参赛队人工审核、修改和确认。
