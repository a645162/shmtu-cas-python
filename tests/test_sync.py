"""Sync 模块单元测试 (使用 FakeAuth + IncrementalBillStore)."""

from __future__ import annotations

from typing import Any

import pytest

from shmtu_cas import (
    BillItem,
    BillType,
    IncrementalBillStore,
    SyncOptions,
    SyncRangePreset,
    SyncStatusKind,
    sync_account,
    sync_accounts_parallel,
)
from shmtu_cas.session.models import LoginProbe
from shmtu_cas.sync.engine import (
    AccountContext,
    AccountSyncJob,
    incremental_sync,
)


def _make_bill(number: str, money: float = 10.0, ts: int = 1000) -> BillItem:
    return BillItem.new_single(
        date_str="2026.05.21",
        time_str="123045",
        time_str_formatted="12:30:45",
        date_time_formatted="2026.05.21 12:30:45",
        timestamp=ts,
        item_type="消费",
        number=number,
        target_user="食堂",
        money_str=f"{money:.2f}",
        money=money,
        method="刷卡",
        status_str="交易成功",
    )


class FakeAuth:
    """Fake EpayAuth: 返回预置 HTML 页面."""

    def __init__(self, pages: list[str]) -> None:
        self._pages = pages
        self.calls: list[tuple[int, str]] = []

    async def probe_login(self) -> Any:
        return LoginProbe.already_logged_in()

    async def get_bill(self, page_no: int, tab_no: str = "1") -> str:
        self.calls.append((page_no, tab_no))
        idx = page_no - 1
        if idx < len(self._pages):
            return self._pages[idx]
        return "<html><body>empty</body></html>"


def _wrap_html(bills_html: str, total_pages: int = 1) -> str:
    return f"""
    <html><body>
        <span><table><tbody>{bills_html}</tbody></table></span>
        <div><table><tbody><tr><td>当前1/{total_pages}页</td></tr></tbody></table></div>
    </body></html>
    """


def _make_bill_tr(number: str, money: str = "10.00") -> str:
    return f"""
    <tr>
        <td>
            <div>2026.05.21</div>
            <div>123045</div>
        </td>
        <td>
            <div>消费</div>
            <div>交易号: {number}</div>
        </td>
        <td>食堂</td>
        <td>{money}</td>
        <td>刷卡</td>
        <td>交易成功</td>
    </tr>
    """


def _multi_bill_trs(numbers: list[str]) -> str:
    return "".join(_make_bill_tr(num) for num in numbers)


@pytest.mark.asyncio
async def test_incremental_sync_collects_new_bills() -> None:
    auth = FakeAuth(
        [_wrap_html(_multi_bill_trs(["2026052113533629001", "2026052113533629002"]), total_pages=1)]
    )
    store = IncrementalBillStore()

    opts = SyncOptions(
        start_page=1,
        max_pages=10,
        bill_type=BillType.ALL,
        early_stop_threshold=5,
        since_timestamp=None,
    )

    result = await incremental_sync(auth, store, opts)

    assert result.new_count == 2
    assert len(store.all_bills()) == 2
    assert {b.number for b in store.all_bills()} == {
        "2026052113533629001",
        "2026052113533629002",
    }


@pytest.mark.asyncio
async def test_incremental_sync_early_stop_on_known() -> None:
    """已知条目连续出现 N 次应触发早停."""
    auth = FakeAuth(
        [
            _wrap_html(
                _multi_bill_trs(["2026052113533629001", "2026052113533629002"]),
                total_pages=5,
            ),
            _wrap_html(
                _multi_bill_trs(["2026052113533629001", "2026052113533629002"]),
                total_pages=5,
            ),
            _wrap_html(
                _multi_bill_trs(["2026052113533629001", "2026052113533629002"]),
                total_pages=5,
            ),
        ]
    )
    store = IncrementalBillStore()
    store.merge(
        [_make_bill("2026052113533629001"), _make_bill("2026052113533629002")]
    )  # 预置已知

    opts = SyncOptions(
        start_page=1,
        max_pages=10,
        bill_type=BillType.ALL,
        early_stop_threshold=3,
    )

    result = await incremental_sync(auth, store, opts)
    assert result.early_stopped is True
    assert result.new_count == 0
    assert result.pages_fetched <= 3


@pytest.mark.asyncio
async def test_sync_account_progress_callback() -> None:
    auth = FakeAuth([_wrap_html(_multi_bill_trs(["2026052113533629001"]), total_pages=1)])
    store = IncrementalBillStore()
    events: list[SyncStatusKind] = []

    async def on_progress(progress: Any) -> None:
        events.append(progress.status.kind)

    ctx = AccountContext(
        account_id="acc-1", account_label="tester", account_index=0, total_accounts=1
    )
    result = await sync_account(auth, store, ctx, on_progress=on_progress)

    assert result.new_count == 1
    assert SyncStatusKind.PROBING_LOGIN in events
    assert SyncStatusKind.SYNCING in events
    assert SyncStatusKind.COMPLETED in events


@pytest.mark.asyncio
async def test_sync_accounts_parallel_aggregates() -> None:
    auth1 = FakeAuth(
        [_wrap_html(_multi_bill_trs(["2026052113533629001", "2026052113533629002"]), total_pages=1)]
    )
    auth2 = FakeAuth(
        [_wrap_html(_multi_bill_trs(["2026052113533629003"]), total_pages=1)]
    )
    store1 = IncrementalBillStore()
    store2 = IncrementalBillStore()

    jobs = [
        AccountSyncJob(
            context=AccountContext(account_id="1", account_label="acc1"),
            auth=auth1,
            store=store1,
        ),
        AccountSyncJob(
            context=AccountContext(account_id="2", account_label="acc2"),
            auth=auth2,
            store=store2,
        ),
    ]

    summary = await sync_accounts_parallel(jobs)
    assert summary.total_new_count == 3
    assert summary.success_count == 2
    assert summary.failure_count == 0
    assert summary.all_success is True
