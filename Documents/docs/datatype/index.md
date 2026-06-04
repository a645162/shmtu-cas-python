# shmtu_cas.datatype — 数据类型

> 版本：1.0.0 | 更新日期：2026-06-04

对齐 Rust `datatype/*` 与 Kotlin `datatype/*`。

## BillType (Enum)

账单类型。

| 成员 | 中文 | 解析关键字 |
| --- | --- | --- |
| `INCOME` | 收入 | "收入" / "充值" / "退款" |
| `EXPENSE` | 支出 | "支出" / "消费" / "扣款" |
| `UNKNOWN` | 未知 | fallback |

`BillType.parse(raw_str: str) -> BillType` —— 从原始字符串反解类型。

## BillItem (dataclass)

一条账单的不可变记录，**所有合并 / 求和操作不会修改原对象**。

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

`sum_money(items: Iterable[BillItem]) -> float` —— 累加求和（**不可变**，返回新值）。

## BillItemStatus (dataclass)

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `str` | 原始状态码 |
| `is_success` | `bool` | 是否成功 |
| `is_pending` | `bool` | 是否处理中 |
| `is_failed` | `bool` | 是否失败 |

`BillItemStatus.parse(raw: str) -> BillItemStatus` —— 反解。

## 子页面

- [BillType](/datatype/bill-type) — 枚举与反解
- [BillItem](/datatype/bill-item) — 字段表 + 不可变语义
- [BillItemStatus](/datatype/bill-item-status) — 状态机
