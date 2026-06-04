# shmtu_cas.parser — 解析器

> 版本：1.0.0 | 更新日期：2026-06-04

对齐 Rust `parser/*` 与 Kotlin `parser/*`。

## 账单 HTML

```python
from shmtu_cas import parse_bill_page, parse_bill_list, parse_bill_item, get_total_pages

parse_bill_page(html) -> BillParseResult
parse_bill_list(html) -> list[BillItem]
parse_bill_item(tr_element) -> BillItem
get_total_pages(html) -> int
```

`BillParseResult`:

```python
@dataclass
class BillParseResult:
    bills: list[BillItem]
    total_pages: int
    page_no: int
    tab_no: str
```

## 热水 HTML

```python
from shmtu_cas import parse_hot_water_list

parse_hot_water_list(html) -> list[HotWaterInfo]
```

`HotWaterInfo`:

```python
@dataclass
class HotWaterInfo:
    date: str
    time: str
    place: str
    amount: float
    balance: float
```

## CSV 导出

```python
from shmtu_cas import CsvExporter

exporter = CsvExporter()
exporter.export("bills.csv", bills)              # 自动 UTF-8 BOM (Excel 友好)
exporter.export("bills.csv", bills, encoding="utf-8")
```

## 子页面

- [账单 HTML 解析](/parser/bill)
- [热水 HTML 解析](/parser/hot-water)
- [CSV 导出](/parser/csv-export)
