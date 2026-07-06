# 实训1

- 比赛 / 项目：课程项目
- 小问数量：4
- 初始化时间：2026-07-06T15:17:28+08:00
- 文档语言：zh-CN
- 当前状态：`initialized`

## 项目目标

> 用一段话说明赛题背景、最终交付物和评价重点。不得直接复制题面而不做任务解释。

## 快速开始

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/check_repo.py
python scripts/run_all.py --dry-run
```

## 目录

```text
configs/                 全局配置与随机种子
data/raw/                原始数据，只读
data/interim/            中间数据
data/processed/          可建模数据
data/external/           外部补充数据
docs/                    项目级建模文档
notebooks/               探索性分析，不作为最终运行入口
questions/qN/            每个小问的方案、代码和产物
report/                   论文与附录
scripts/                  仓库级运行和审计脚本
src/modeling_common/      跨小问共享代码
tests/                    基础测试
```

## 运行约定

- 所有命令从仓库根目录执行。
- 每个小问的正式入口是 `questions/qN/scripts/pipeline.py`。
- 图和生图数据必须同名保存。
- 最终结论必须登记到 `docs/evidence_chain.csv`。
- 原始数据首次放入后运行 `python scripts/snapshot_raw.py`。

## 当前小问

| 小问 | 状态 | 主要目标 | 入口 |
|---|---|---|---|
| q1 | done | 等速与等马赫巡航爬升基线比较 | `python questions/q1/scripts/pipeline.py --config configs/default.yaml` |
| q2 | done | 固定 q1 几何路径的标准大气、静力温差修正与路径积分 | `python questions/q2/scripts/pipeline.py --config configs/default.yaml` |
| q3 | in_design | 固定航程巡航最优控制模型设计 | `python questions/q3/scripts/pipeline.py --dry-run` |
| q4 | planned | 待填写 | `python questions/q4/scripts/pipeline.py --dry-run` |

> 初始化脚本不会自动理解题面。请在读取题目后补全本表以及 `docs/problem_statement.md`。
