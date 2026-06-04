# BillItemStatus

> 版本：1.0.0

账单状态机。

```python
from shmtu_cas import BillItemStatus

s = BillItemStatus.parse("01")  # success
print(s.is_success)             # True
print(s.is_pending)             # False
print(s.is_failed)              # False
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `str` | 原始状态码 |
| `is_success` | `bool` | 是否成功 |
| `is_pending` | `bool` | 是否处理中 |
| `is_failed` | `bool` | 是否失败 |

`BillItemStatus.parse(raw: str) -> BillItemStatus` —— 反解原始码为布尔组合。
