# BillStore 接口

> 版本：1.0.0

```python
class BillStore(Protocol):
    def has_timestamp(self, ts: int) -> bool: ...
    def record(self, bill: BillItem) -> None: ...
    def all_timestamps(self) -> set[int]: ...
```

实现 `BillStore` 的两个方法（`has_timestamp` / `record`），就能接入整个同步链路。

## 默认实现

`IncrementalBillStore` 是默认内存实现（`set[int]`）：

```python
from shmtu_cas import IncrementalBillStore

store = IncrementalBillStore()
```

## SQLite 实现示例

```python
import sqlite3
from shmtu_cas import BillItem

class SqliteBillStore:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                number TEXT PRIMARY KEY,
                ts INTEGER NOT NULL,
                data TEXT NOT NULL
            )
        """)
        self.ts_index: set[int] = set(
            row[0] for row in self.conn.execute("SELECT ts FROM bills")
        )

    def has_timestamp(self, ts: int) -> bool:
        return ts in self.ts_index

    def record(self, bill: BillItem) -> None:
        self.ts_index.add(bill.timestamp)
        self.conn.execute(
            "INSERT OR IGNORE INTO bills (number, ts, data) VALUES (?, ?, ?)",
            (bill.number, bill.timestamp, bill.to_json()),
        )
        self.conn.commit()

    def all_timestamps(self) -> set[int]:
        return set(self.ts_index)
```
