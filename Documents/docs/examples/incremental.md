# 增量同步（单账号）

> 版本：1.0.0

```python
import asyncio
from shmtu_cas import (
    EpayAuth, IncrementalBillStore,
    SyncOptions, SyncRangePreset, incremental_sync,
)

async def main():
    async with EpayAuth() as epay:
        store = IncrementalBillStore()
        opts = SyncOptions.incremental(SyncRangePreset.MONTH)

        def on_page(p):
            print(f"page {p.page}/{p.total_pages}, new={p.new_count}")

        result = await incremental_sync(epay, store, opts, on_progress=on_page)
        print(f"新增 {result.new_count} 条, 翻 {result.pages_fetched} 页, 早停={result.early_stopped}")
        for bill in result.new_bills:
            print(bill)

asyncio.run(main())
```
