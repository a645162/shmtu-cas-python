# SyncRangePreset / SyncOptions

> 版本：1.0.0

## SyncRangePreset

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
```

### 工厂方法

```python
opts = SyncOptions.incremental(SyncRangePreset.MONTH)  # 增量同步近 30 天
opts = SyncOptions.full()                                # 全量同步（无限范围 + 不早停）
```
