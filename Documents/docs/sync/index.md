# shmtu_cas.sync — 同步引擎

> 版本：1.0.0 | 更新日期：2026-06-04

对齐 Rust `sync/*` 与 Kotlin `sync/*`。

## 状态机

```python
class SyncStatusKind(Enum):
    PROBING_LOGIN    = "probing_login"
    GETTING_CAPTCHA  = "getting_captcha"
    LOGGING_IN       = "logging_in"
    SYNCING          = "syncing"
    PERSISTING       = "persisting"
    COMPLETED        = "completed"
    FAILED           = "failed"
```

`SyncStatus` dataclass：`{kind, page, total_pages, error}`。

## SyncRangePreset (Enum)

| 成员 | 起始时间 |
| --- | --- |
| `WEEK` | 7 天前 |
| `HALF_MONTH` | 15 天前 |
| `MONTH` | 30 天前 |
| `HALF_YEAR` | 183 天前 |
| `YEAR` | 365 天前 |
| `ALL` | 无限制 |

`since_timestamp() -> int | None` —— 返回 epoch 秒。

## SyncOptions

```python
@dataclass
class SyncOptions:
    start_page: int = 1
    max_pages: int = 50
    range_start_ts: int | None = None
    stop_on_known_timestamp: int | None = None
    early_stop: bool = True

SyncOptions.incremental(SyncRangePreset.MONTH)  # 工厂
SyncOptions.full()
```

## BillStore / IncrementalBillStore

`BillStore` (Protocol)：

```python
class BillStore(Protocol):
    def has_timestamp(self, ts: int) -> bool: ...
    def record(self, bill: BillItem) -> None: ...
    def all_timestamps(self) -> set[int]: ...
```

`IncrementalBillStore` 是默认内存实现（`set[int]`）。

## 同步入口

```python
async def incremental_sync(
    epay: EpayAuth, store: BillStore, options: SyncOptions,
    *, on_progress: Callable[[SyncPageProgress], None | Awaitable[None]] = None,
) -> SyncResult

async def full_sync(...) -> SyncResult

async def sync_account(job: AccountSyncJob, on_progress=...) -> AccountSyncResult

async def sync_accounts_parallel(
    jobs: list[AccountSyncJob], on_progress=...,
    *, max_concurrency: int | None = None,
) -> ParallelSyncSummary
```

`SyncResult`:

```python
@dataclass
class SyncResult:
    new_bills: list[BillItem]
    new_count: int
    pages_fetched: int
    early_stopped: bool
    duration_ms: int
    status: SyncStatus
```

`ParallelSyncSummary`:

```python
@dataclass
class ParallelSyncSummary:
    success_count: int
    failure_count: int
    total_new_count: int
    per_account: list[AccountSyncResult]
```

## AccountSyncJob

```python
@dataclass
class AccountSyncJob:
    context: AccountContext                # account_label + 描述
    auth: EpayAuth                         # 每个账号独立 auth 实例
    store: BillStore
    options: SyncOptions = SyncOptions.incremental(SyncRangePreset.MONTH)
```

## 子页面

- [状态机与进度](/sync/state-machine)
- [SyncRangePreset / SyncOptions](/sync/options)
- [BillStore 接口](/sync/bill-store)
- [同步入口函数](/sync/entry-points)
