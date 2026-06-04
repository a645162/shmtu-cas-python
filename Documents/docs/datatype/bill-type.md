# BillType

> 版本：1.0.0

账单类型枚举，对齐 Rust `BillType` 与 Kotlin `BillType`。

```python
from shmtu_cas import BillType

# 直接使用枚举
t = BillType.INCOME

# 从原始字符串反解
t = BillType.parse("收入")     # BillType.INCOME
t = BillType.parse("支出")     # BillType.EXPENSE
t = BillType.parse("??")       # BillType.UNKNOWN
```

| 成员 | 中文 | 解析关键字 |
| --- | --- | --- |
| `INCOME` | 收入 | "收入" / "充值" / "退款" |
| `EXPENSE` | 支出 | "支出" / "消费" / "扣款" |
| `UNKNOWN` | 未知 | fallback |
