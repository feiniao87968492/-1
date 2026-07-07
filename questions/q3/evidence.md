# q3 证据说明

本文件解释本小问关键主张的证据。机器可读索引仍以 `docs/evidence_chain.csv` 为准。

| Claim ID | 主张 | 证据 | 验证 | 局限 | 状态 |
|---|---|---|---|---|---|
| Q3-C01 | 第三问应采用固定航程、终端质量自由的最优控制口径，不能固定 `m(tf)=62000 kg` 后再最小化油耗 | `questions/q3/review.md`; `questions/q3/approach.md` | 目标函数退化分析：固定终端质量时 `J=m0-mf` 为常数 | 尚未进行数值求解 | planned |
| Q3-C02 | 主方案固定终端高度和速度，以避免通过降低终端机械能获得虚假省油 | `questions/q3/review.md`; `questions/q3/approach.md`; `questions/q3/derivation.md` | 终端条件已写入优化问题定义 | 终端能量高度替代方案仅列为扩展 | planned |
| Q3-C03 | 直接法作为主求解方法，PMP 必要条件作为诊断验证 | `questions/q3/approach.md`; `questions/q3/derivation.md` | Hamiltonian、控制驻值和直接配点方案已记录 | 还需第二轮实现脚本和数值验证 | planned |
| Q3-C04 | 在 `Xf=189781.310 m` 下，q2 有风固定路径基线可行，但同一路径无风重算不满足 `m>=62000 kg` | `questions/q3/artifacts/tables/baseline_feasibility.csv`; `questions/q3/q3_review1_audit.md` | `questions/q3/scripts/precheck.py` 生成配置风场和无风两行；距离误差为 0，燃油积分与质量亏损误差小于 `0.05 kg` | 只验证固定 q1 路径，不证明无风优化问题整体不可行 | supported |
