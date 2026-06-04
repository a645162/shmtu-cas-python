# 多账号并行同步

> 版本：1.0.0

```python
import asyncio
from shmtu_cas import (
    EpayAuth, IncrementalBillStore,
    AccountContext, AccountSyncJob, sync_accounts_parallel,
)

async def main():
    def make_account(label: str) -> AccountSyncJob:
        return AccountSyncJob(
            context=AccountContext(account_label=label),
            auth=EpayAuth(),
            store=IncrementalBillStore(),
        )

    jobs = [make_account("acc1"), make_account("acc2")]

    async def on_progress(p):
        print(p.to_message())

    summary = await sync_accounts_parallel(jobs, on_progress=on_progress)
    print(f"汇总: 成功 {summary.success_count}, 失败 {summary.failure_count}, 新增 {summary.total_new_count}")

asyncio.run(main())
```
