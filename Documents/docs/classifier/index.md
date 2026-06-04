# shmtu_cas.classifier — 分类与翻译

> 版本：1.0.0 | 更新日期：2026-06-04

## BillClassifier

```python
from shmtu_cas import BillClassifier

BillClassifier.from_json(json_str)   # 或 .from_dict(dict)
BillClassifier(rules: list[CategoryRule])
classifier.classify(item_name: str, target: str = "") -> BillCategory
```

`BillCategory` (Enum)：`DEPOSIT` / `BATH` / `CANTEEN` / `SHOPPING` / `TRANSPORT` / `OTHER` / `UNKNOWN`。

`CategoryRule` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `category` | `BillCategory` | 目标分类 |
| `name_keywords` | `list[str]` | 交易名包含 |
| `target_keywords` | `list[str]` | target_user 包含 |
| `priority` | `int` | 匹配优先级（越大越优先） |

## PositionTranslator

把 `海馨楼食堂-1F` 拆为 `(position='海馨楼', room='海馨第1食堂')`。

```python
from shmtu_cas import PositionTranslator

PositionTranslator.from_json(json_str)   # JSON 含 field + keywords
translator.translate(raw: str) -> PositionEntry | None
```

`PositionEntry`:

```python
@dataclass
class PositionEntry:
    position: str    # 大楼
    room: str        # 房间/楼层
```

## 子页面

- [BillClassifier](/classifier/bill-classifier)
- [PositionTranslator](/classifier/position-translator)
