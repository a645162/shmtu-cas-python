"""账单同步引擎 — 对齐 Rust ``sync/mod.rs`` 与 Kotlin ``sync/BillSync``."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Awaitable, Callable, Generic, Iterable, Protocol, TypeVar, Union, runtime_checkable
from uuid import uuid4

from ..auth.epay import EpayAuth
from ..datatype.bill import BillItem, BillType
from ..parser.bill import parse_bill_page

# =================== 内部 Result 类型 (避免依赖外部库) ===================

_T = TypeVar("_T")
_E = TypeVar("_E", bound=Exception)


class _Ok(Generic[_T]):
    __slots__ = ("_value",)

    def __init__(self, value: _T) -> None:
        self._value = value

    @property
    def is_ok(self) -> bool:
        return True

    def unwrap(self) -> _T:
        return self._value


class _Err(Generic[_E]):
    __slots__ = ("_error",)

    def __init__(self, error: _E) -> None:
        self._error = error

    @property
    def is_ok(self) -> bool:
        return False

    def unwrap(self) -> _E:  # type: ignore[return-value]
        return self._error


Result = Union[_Ok, _Err]


# =================== 状态机 ===================


class SyncStatusKind(Enum):
    """同步状态机节点 — 对齐 Kotlin ``SyncStatus`` sealed class."""

    PROBING_LOGIN = "probing_login"
    GETTING_CAPTCHA = "getting_captcha"
    LOGGING_IN = "logging_in"
    SYNCING = "syncing"
    PERSISTING = "persisting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncStatus:
    """同步状态 — 对齐 Kotlin ``SyncStatus``."""

    kind: SyncStatusKind
    page: int = 0
    total_pages: int = 0
    error: str = ""


# =================== 同步范围预设 ===================


class SyncRangePreset(Enum):
    """同步时间范围预设 — 对齐 Kotlin ``SyncRangePreset``."""

    WEEK = "week"
    HALF_MONTH = "half_month"
    MONTH = "month"
    HALF_YEAR = "half_year"
    YEAR = "year"
    ALL = "all"

    def since_timestamp(self) -> int | None:
        """返回该范围对应的 epoch 秒 (秒级精度, 与 Rust 保持一致)."""
        if self is SyncRangePreset.ALL:
            return None
        now = datetime.now(tz=timezone.utc)
        match self:
            case SyncRangePreset.WEEK:
                delta = timedelta(days=7)
            case SyncRangePreset.HALF_MONTH:
                delta = timedelta(days=15)
            case SyncRangePreset.MONTH:
                delta = timedelta(days=30)
            case SyncRangePreset.HALF_YEAR:
                delta = timedelta(days=183)
            case SyncRangePreset.YEAR:
                delta = timedelta(days=365)
            case _:
                return None
        return int((now - delta).timestamp())


# =================== 同步选项 ===================


@dataclass
class SyncOptions:
    """同步选项 — 对齐 Rust ``SyncOptions`` 与 Kotlin ``SyncOptions``."""

    start_page: int = 1
    max_pages: int = 50
    bill_type: BillType = BillType.ALL
    early_stop_threshold: int = 3
    since_timestamp: int | None = None
    clear_before_merge: bool = False

    def __post_init__(self) -> None:
        if self.start_page < 1:
            msg = "start_page must be >= 1"
            raise ValueError(msg)
        if self.max_pages < 1:
            msg = "max_pages must be >= 1"
            raise ValueError(msg)
        if self.early_stop_threshold < 1:
            msg = "early_stop_threshold must be >= 1"
            raise ValueError(msg)

    @classmethod
    def incremental(cls, range_preset: SyncRangePreset = SyncRangePreset.MONTH) -> SyncOptions:
        """增量快捷构造. 对齐 Kotlin ``SyncOptions.incremental``."""
        return cls(
            start_page=1,
            max_pages=100,
            bill_type=BillType.ALL,
            early_stop_threshold=10,
            since_timestamp=range_preset.since_timestamp(),
        )

    @classmethod
    def full(cls, range_preset: SyncRangePreset = SyncRangePreset.ALL) -> SyncOptions:
        """全量快捷构造. 对齐 Kotlin ``SyncOptions.full``."""
        return cls(
            start_page=1,
            max_pages=1000,
            bill_type=BillType.ALL,
            early_stop_threshold=2**31 - 1,  # 关闭早停
            since_timestamp=range_preset.since_timestamp(),
            clear_before_merge=True,
        )


# =================== 进度回调 ===================


@dataclass
class SyncPageProgress:
    """单页拉取进度 — 对齐 Rust ``SyncPageProgress``."""

    page: int
    total_pages: int
    new_count: int


@dataclass
class SyncResult:
    """单次同步结果 — 对齐 Rust ``SyncResult``."""

    new_count: int
    pages_fetched: int
    early_stopped: bool
    new_bills: list[BillItem] = field(default_factory=list)


@dataclass
class SyncProgress:
    """顶层同步进度 (带账号上下文). 对齐 Kotlin ``SyncProgress``."""

    account_id: str
    current_account: str
    account_index: int
    total_accounts: int
    new_count: int
    pages_fetched: int
    total_new_count: int
    status: SyncStatus

    def to_message(self) -> str:
        s = self.status
        match s.kind:
            case SyncStatusKind.PROBING_LOGIN:
                return (
                    f"账号 {self.current_account} 正在检查登录状态"
                    f"（{self.account_index + 1}/{self.total_accounts}）"
                )
            case SyncStatusKind.GETTING_CAPTCHA:
                return (
                    f"账号 {self.current_account} 需要验证码"
                    f"（{self.account_index + 1}/{self.total_accounts}），"
                    f"累计新增 {self.total_new_count} 条"
                )
            case SyncStatusKind.LOGGING_IN:
                return (
                    f"账号 {self.current_account} 已通过登录检查"
                    f"（{self.account_index + 1}/{self.total_accounts}），"
                    f"累计新增 {self.total_new_count} 条"
                )
            case SyncStatusKind.SYNCING:
                return (
                    f"账号 {self.current_account} 正在拉取账单第 {s.page}/{s.total_pages} 页，"
                    f"当前账号新增 {self.new_count} 条，"
                    f"累计新增 {self.total_new_count} 条"
                    f"（{self.account_index + 1}/{self.total_accounts}）"
                )
            case SyncStatusKind.PERSISTING:
                return (
                    f"账号 {self.current_account} 拉取完成，正在写入存储: "
                    f"新增 {self.new_count} 条，拉取 {self.pages_fetched} 页，"
                    f"累计新增 {self.total_new_count} 条"
                    f"（{self.account_index + 1}/{self.total_accounts}）"
                )
            case SyncStatusKind.COMPLETED:
                return (
                    f"账号 {self.current_account} 同步完成: 新增 {self.new_count} 条，"
                    f"拉取 {self.pages_fetched} 页，累计新增 {self.total_new_count} 条"
                    f"（{self.account_index + 1}/{self.total_accounts}）"
                )
            case SyncStatusKind.FAILED:
                return (
                    f"账号 {self.current_account} 同步失败"
                    f"（{self.account_index + 1}/{self.total_accounts}）：{s.error}"
                )


# =================== 账单存储 ===================


@runtime_checkable
class BillStore(Protocol):
    """账单存储抽象 — 对齐 Rust ``BillStore`` trait 与 Kotlin ``BillStore`` 接口.

    实现此接口对接 SQLite / JSON / 内存等任意后端.
    """

    def contains(self, transaction_no: str) -> bool:
        ...

    def merge(self, new_bills: list[BillItem]) -> None:
        ...

    def clear(self) -> None:  # pragma: no cover - default
        ...


class IncrementalBillStore:
    """基于 ``set[str]`` 的内存去重器, 适合做最小可运行的 demo.

    生产环境请实现自己的 ``BillStore`` 协议并对接持久化层.
    """

    def __init__(self) -> None:
        self._numbers: set[str] = set()
        self._bills: list[BillItem] = []

    def contains(self, transaction_no: str) -> bool:
        return transaction_no in self._numbers

    def merge(self, new_bills: list[BillItem]) -> None:
        for bill in new_bills:
            if bill.number and bill.number not in self._numbers:
                self._numbers.add(bill.number)
                self._bills.append(bill)

    def clear(self) -> None:
        self._numbers.clear()
        self._bills.clear()

    def all_bills(self) -> list[BillItem]:
        return list(self._bills)


# =================== 多账号上下文 ===================


@dataclass
class AccountContext:
    """账号上下文 — 对齐 Kotlin ``AccountContext``."""

    account_id: str = field(default_factory=lambda: str(uuid4()))
    account_label: str = ""
    account_index: int = 0
    total_accounts: int = 1


@dataclass
class AccountSyncJob:
    """单账号同步任务 — 对齐 Kotlin ``AccountSyncJob``."""

    context: AccountContext
    auth: EpayAuth
    store: BillStore


@dataclass
class AccountSyncResult:
    """单账号同步结果."""

    context: AccountContext
    result: Result  # _Ok[SyncResult] | _Err[Exception]


@dataclass
class ParallelSyncSummary:
    """多账号并行同步汇总 — 对齐 Kotlin ``ParallelSyncSummary``."""

    results: list[AccountSyncResult]
    total_new_count: int
    success_count: int
    failure_count: int

    @property
    def all_success(self) -> bool:
        return self.failure_count == 0


# =================== 顶层 API ===================


ProgressCallback = Callable[[SyncProgress], None]
AsyncProgressCallback = Callable[[SyncProgress], Awaitable[None]]


async def _emit_progress(
    callback: ProgressCallback | AsyncProgressCallback | None,
    progress: SyncProgress,
) -> None:
    if callback is None:
        return
    result = callback(progress)
    if asyncio.iscoroutine(result):
        await result


async def _run_sync(
    auth: EpayAuth,
    store: BillStore,
    options: SyncOptions,
    on_page_progress: Callable[[SyncPageProgress], None] | Callable[[SyncPageProgress], Awaitable[None]] | None = None,
    full_sync: bool = False,
) -> SyncResult:
    """翻页循环核心. 对齐 Rust ``incremental_sync_with_progress`` 与 Kotlin ``runSync``."""
    tab_no = options.bill_type.tab_no

    if full_sync and options.clear_before_merge:
        try:
            store.clear()
        except Exception:  # noqa: BLE001
            pass

    new_bills: list[BillItem] = []
    pages_fetched = 0
    consecutive_known = 0
    early_stopped = False
    reached_time_boundary = False
    last_total_pages = options.max_pages  # noqa: F841 — kept for parity with Rust
    seen_numbers: set[str] = set()

    async def _emit_page(p: SyncPageProgress) -> None:
        if on_page_progress is None:
            return
        result = on_page_progress(p)
        if asyncio.iscoroutine(result):
            await result

    for page_offset in range(options.max_pages):
        page_no = options.start_page + page_offset
        try:
            html = await auth.get_bill(page_no=page_no, tab_no=tab_no)
        except RuntimeError:
            break

        page_result = parse_bill_page(html)
        if not page_result.bills and page_offset == 0:
            break
        pages_fetched += 1

        for bill in page_result.bills:
            if options.since_timestamp is not None and bill.timestamp < options.since_timestamp:
                reached_time_boundary = True
                break

            is_known = (
                bool(bill.number)
                and (store.contains(bill.number) or bill.number in seen_numbers)
            )
            if is_known:
                consecutive_known += 1
                if consecutive_known >= options.early_stop_threshold:
                    early_stopped = True
                    break
            else:
                consecutive_known = 0
                if bill.number:
                    seen_numbers.add(bill.number)
                new_bills.append(bill)

        await _emit_page(
            SyncPageProgress(
                page=page_no,
                total_pages=max(page_result.total_pages, page_no),
                new_count=len(new_bills),
            )
        )

        if early_stopped:
            break
        if reached_time_boundary:
            break
        if page_no >= page_result.total_pages:
            break

    store.merge(new_bills)
    return SyncResult(
        new_count=len(new_bills),
        pages_fetched=pages_fetched,
        early_stopped=early_stopped,
        new_bills=new_bills,
    )


async def incremental_sync(
    auth: EpayAuth,
    store: BillStore,
    options: SyncOptions | None = None,
    on_progress: ProgressCallback | AsyncProgressCallback | None = None,
) -> SyncResult:
    """增量同步账单 (单账号). 对齐 Rust ``incremental_sync`` 与 Kotlin ``incrementalSync``."""
    opts = options or SyncOptions.incremental()

    async def _on_page(p: SyncPageProgress) -> None:
        if on_progress is None:
            return
        progress = SyncProgress(
            account_id="",
            current_account="",
            account_index=0,
            total_accounts=1,
            new_count=p.new_count,
            pages_fetched=p.page - opts.start_page + 1,
            total_new_count=p.new_count,
            status=SyncStatus(
                kind=SyncStatusKind.SYNCING,
                page=p.page,
                total_pages=p.total_pages,
            ),
        )
        await _emit_progress(on_progress, progress)

    result = await _run_sync(auth, store, opts, on_page_progress=_on_page, full_sync=False)

    if on_progress is not None:
        await _emit_progress(
            on_progress,
            SyncProgress(
                account_id="",
                current_account="",
                account_index=0,
                total_accounts=1,
                new_count=result.new_count,
                pages_fetched=result.pages_fetched,
                total_new_count=result.new_count,
                status=SyncStatus(
                    kind=SyncStatusKind.PERSISTING
                    if result.new_count
                    else SyncStatusKind.SYNCING,
                    page=opts.start_page,
                    total_pages=opts.start_page + result.pages_fetched,
                ),
            ),
        )
        await _emit_progress(
            on_progress,
            SyncProgress(
                account_id="",
                current_account="",
                account_index=0,
                total_accounts=1,
                new_count=result.new_count,
                pages_fetched=result.pages_fetched,
                total_new_count=result.new_count,
                status=SyncStatus(kind=SyncStatusKind.COMPLETED),
            ),
        )
    return result


async def full_sync(
    auth: EpayAuth,
    store: BillStore,
    options: SyncOptions | None = None,
) -> SyncResult:
    """全量同步账单 (单账号). 对齐 Kotlin ``fullSync``."""
    opts = options or SyncOptions.full()
    return await _run_sync(auth, store, opts, on_page_progress=None, full_sync=True)


async def sync_account(
    auth: EpayAuth,
    store: BillStore,
    context: AccountContext,
    on_progress: ProgressCallback | AsyncProgressCallback | None = None,
) -> SyncResult:
    """单账号同步包装器. 对齐 Kotlin ``syncAccount`` 增量部分.

    假定已登录; 业务层使用 ``EpayAuth`` 完成登录后再调用.
    """
    opts = SyncOptions.incremental(SyncRangePreset.MONTH)

    if on_progress is not None:
        await _emit_progress(
            on_progress,
            SyncProgress(
                account_id=context.account_id,
                current_account=context.account_label,
                account_index=context.account_index,
                total_accounts=context.total_accounts,
                new_count=0,
                pages_fetched=0,
                total_new_count=0,
                status=SyncStatus(kind=SyncStatusKind.PROBING_LOGIN),
            ),
        )

    probe = await auth.probe_login()
    if probe.is_need_login:
        msg = (
            f"账号 {context.account_label} 未登录, 请先调用 EpayAuth 完成登录"
        )
        if on_progress is not None:
            await _emit_progress(
                on_progress,
                SyncProgress(
                    account_id=context.account_id,
                    current_account=context.account_label,
                    account_index=context.account_index,
                    total_accounts=context.total_accounts,
                    new_count=0,
                    pages_fetched=0,
                    total_new_count=0,
                    status=SyncStatus(kind=SyncStatusKind.FAILED, error=msg),
                ),
            )
        raise RuntimeError(msg)

    def _make_progress(new_count: int, pages_fetched: int, total: int) -> SyncProgress:
        return SyncProgress(
            account_id=context.account_id,
            current_account=context.account_label,
            account_index=context.account_index,
            total_accounts=context.total_accounts,
            new_count=new_count,
            pages_fetched=pages_fetched,
            total_new_count=new_count,
            status=SyncStatus(
                kind=SyncStatusKind.SYNCING,
                page=opts.start_page + pages_fetched - 1,
                total_pages=total,
            ),
        )

    async def _on_page(p: SyncPageProgress) -> None:
        if on_progress is None:
            return
        progress = _make_progress(p.new_count, p.page - opts.start_page + 1, p.total_pages)
        await _emit_progress(on_progress, progress)

    result = await _run_sync(auth, store, opts, on_page_progress=_on_page, full_sync=False)
    if on_progress is not None:
        await _emit_progress(
            on_progress,
            SyncProgress(
                account_id=context.account_id,
                current_account=context.account_label,
                account_index=context.account_index,
                total_accounts=context.total_accounts,
                new_count=result.new_count,
                pages_fetched=result.pages_fetched,
                total_new_count=result.new_count,
                status=SyncStatus(kind=SyncStatusKind.COMPLETED),
            ),
        )
    return result


async def sync_accounts_parallel(
    jobs: Iterable[AccountSyncJob],
    on_progress: ProgressCallback | AsyncProgressCallback | None = None,
) -> ParallelSyncSummary:
    """多账号并行同步. 对齐 Kotlin ``syncAccountsParallel``."""
    job_list = list(jobs)
    total_accounts = len(job_list)
    if total_accounts == 0:
        return ParallelSyncSummary(
            results=[], total_new_count=0, success_count=0, failure_count=0
        )

    total_new_lock = asyncio.Lock()
    total_new = 0

    async def _run_one(idx: int, job: AccountSyncJob) -> AccountSyncResult:
        nonlocal total_new

        async def _wrap(progress: SyncProgress) -> None:
            progress.account_index = idx
            progress.total_accounts = total_accounts
            if on_progress is not None:
                await _emit_progress(on_progress, progress)

        try:
            result = await sync_account(job.auth, job.store, job.context, on_progress=_wrap)
            async with total_new_lock:
                total_new += result.new_count
            return AccountSyncResult(context=job.context, result=_Ok(result))
        except Exception as e:  # noqa: BLE001
            return AccountSyncResult(context=job.context, result=_Err(e))

    results = await asyncio.gather(*(_run_one(idx, job) for idx, job in enumerate(job_list)))

    success_count = sum(1 for r in results if r.result.is_ok)
    return ParallelSyncSummary(
        results=results,
        total_new_count=total_new,
        success_count=success_count,
        failure_count=len(results) - success_count,
    )
