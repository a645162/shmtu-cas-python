# 状态机与进度

> 版本：1.0.0

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

`SyncStatus` dataclass：

```python
@dataclass
class SyncStatus:
    kind: SyncStatusKind
    page: int | None = None
    total_pages: int | None = None
    error: str | None = None
```

## 回调签名

```python
async def incremental_sync(
    epay, store, opts,
    *, on_progress: Callable[[SyncPageProgress], None | Awaitable[None]] = None,
) -> SyncResult
```

回调可以是同步函数或异步协程，库内部会用 `inspect.iscoroutinefunction` 自动 `await`。
