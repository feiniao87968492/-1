# Data Layout

## raw

原始数据，只读。不得把清洗后文件写回此目录。首次放入数据后运行：

```bash
python scripts/snapshot_raw.py
```

## interim

可重复生成的中间数据，例如合并、编码或初步清洗结果。

## processed

直接用于建模的最终数据集。每个文件应能由脚本从 `raw/` 和 `external/` 重建。

## external

外部补充数据。必须在 `docs/data_dictionary.md` 和 `docs/references.md` 记录来源、访问日期和许可说明。
