# CSV 导出

> 版本：1.0.0

```python
from shmtu_cas import CsvExporter, parse_bill_page

result = parse_bill_page(html)

exporter = CsvExporter()
exporter.export("bills.csv", result.bills)              # 默认 UTF-8 BOM
exporter.export("bills.csv", result.bills, encoding="utf-8-sig")
```

- **自动 UTF-8 BOM**：Excel 打开 CSV 时不会中文乱码
- 字段顺序对齐 `BillItem` 字段定义
- 不可变：`bills` 中的元素不会被修改
