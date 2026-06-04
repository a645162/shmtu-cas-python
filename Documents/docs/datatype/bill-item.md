# BillItem

> 版本：1.0.0

一条账单的不可变记录，**所有合并 / 求和操作不会修改原对象**。

```python
from shmtu_cas import BillItem, sum_money

item = BillItem(
    date_str="2026.06.04",
    time_str="123000",
    timestamp=1749000000,
    item_type="食堂消费",
    number="202606040001",
    target_user="海馨楼食堂-1F",
    money_str="-12.50",
    money=-12.50,
    method="校园卡",
    is_combined=False,
    account_id="20210000",
)

# 不可变：求和不修改原 item
total = sum_money([item, item])   # -25.0
```

## 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `date_str` | `str` | 日期字符串（原始格式 `YYYY.MM.DD`） |
| `time_str` | `str` | 时间字符串（原始 `HHMMSS`） |
| `timestamp` | `int` | Unix 秒（用于增量同步） |
| `item_type` | `str` | 交易名称（"食堂消费"、"微信充值"） |
| `number` | `str` | 交易号 |
| `target_user` | `str` | 对方账户 / 位置 |
| `money_str` | `str` | 金额字符串（原始） |
| `money` | `float` | 金额数值（**正=收入，负=支出**） |
| `method` | `str` | 支付方式 |
| `is_combined` | `bool` | 是否为合并记录 |
| `account_id` | `str` | 所属学号 |

## 不可变语义

- `BillItem` 是 `frozen=True` 的 dataclass
- `sum_money()` 返回新 `float`，不会改变原对象
- 合并记录通过 `is_combined=True` 标记，原始 `number` 仍存在
