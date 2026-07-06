# 证据链使用说明

`evidence_chain.csv` 是项目结论的机器可读索引。

## 状态

- `planned`：准备验证；
- `supported`：已有数据、脚本、产物和验证支持；
- `rejected`：实验不支持；
- `superseded`：被更完整结论替代。

## 最低要求

状态为 `supported` 的记录必须填写：

- `data_source`
- `script`
- `config`
- `artifact`
- `validation`

论文中的关键数值、排名、最优方案、预测结论和机制解释都应有对应记录。
