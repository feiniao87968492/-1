# q1 实验记录

## 实验矩阵

| 实验 ID | 日期 | 目标 | 数据版本 | 模型 / 配置 | 指标 | 结果 | 决策 |
|---|---|---|---|---|---|---|---|
| q1-E01 | 2026-07-06 | 基线等速巡航爬升 | `question.md` + 用户风场 `3e-5` | `questions/q1/scripts/pipeline.py --config configs/default.yaml` | `tf, xf, hf, climb_rate` | `tf=761.917 s`, `xf=200668.442 m`, `hf=10637.065 m` | 作为 q1 基线 |
| q1-E02 | 2026-07-06 | 等马赫巡航爬升 | 同上 | 同上 | `tf, xf, hf, climb_rate` | `tf=811.032 s`, `xf=211331.296 m`, `hf=10437.818 m` | 与基线对比 |
| q1-E03 | 2026-07-06 | 验证与诊断 | 生成剖面数据 | `questions/q1/scripts/validate.py` | 残差、单调性、步长敏感性、风场对比 | 全部验证项通过 | 支持主结果 |
| q1-E04 | 2026-07-06 | 参数敏感性 | 生成剖面数据 | `questions/q1/scripts/validate.py` | `cT` 对照、`beta` 按配置 `[-20%, -10%, +10%, +20%]` 扰动 | 见 `sensitivity_summary.csv` | 记录为稳健性证据 |

## 失败实验

无失败数值实验。题意审计阶段拒绝了严格水平飞行模型和 `T=D` 爬升模型，理由见 `questions/q1/review.md` 与 `questions/q1/approach.md`。

## 参数搜索

| 参数 | 搜索范围 | 方法 | 最终值 | 选择依据 |
|---|---|---|---|---|
| 风场系数 | `3e-6`, `3e-5`, 题面/OCR | 人工确认 | `3e-5` | 用户明确指定，且与 OCR 题面 `0.00003` 一致 |
| `cT` | `2.8e-4`, `2.8e-5` | 主结果 + 工程合理性对照 | 主结果 `2.8e-4` | 题面参数；`2.8e-5` 只作敏感性 |
| `beta` | 标称值 `-20%`, `-10%`, `+10%`, `+20%` | 敏感性分析 | `0.003` | 题面参数；扰动网格来自 `configs/default.yaml` |

## 复现命令

```bash
python questions/q1/scripts/pipeline.py --config configs/default.yaml
python questions/q1/scripts/validate.py --config configs/default.yaml
```
