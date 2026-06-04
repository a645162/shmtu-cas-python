# 同步入口函数

> 版本：1.0.0

## 单账号

```python
from shmtu_cas import (
    EpayAuth, IncrementalBillStore,
    SyncOptions, SyncRangePreset, incremental_sync,
)

async with EpayAuth() as epay:
    store = IncrementalBillStore()
    opts = SyncOptions.incremental(SyncRangePreset.MONTH)
    result = await incremental_sync(epay, store, opts, on_progress=lambda p: print(p))
```

`full_sync(...)` 用法相同，区别是不设上限、关闭早停。

## 多账号并行

```python
from shmtu_cas import (
    EpayAuth, IncrementalBillStore,
    AccountContext, AccountSyncJob, sync_accounts_parallel,
)

jobs = [
    AccountSyncJob(
        context=AccountContext(account_label="acc1"),
        auth=EpayAuth(),
        store=IncrementalBillStore(),
    ),
    AccountSyncJob(
        context=AccountContext(account_label="acc2"),
        auth=EpayAuth(),
        store=IncrementalBillStore(),
    ),
]

summary = await sync_accounts_parallel(jobs, on_progress=print)
print(f"汇总: 成功 {summary.success_count}, 失败 {summary.failure_count}, 新增 {summary.total_new_count}")
```

## AccountSyncJob

```python
@dataclass
class AccountSyncJob:
    context: AccountContext
    auth: EpayAuth
    store: BillStore
    options: SyncOptions = SyncOptions.incremental(SyncRangePreset.MONTH)
```

`AccountContext` 至少需要 `account_label`，库内会把它原样回传到回调与结果中。
