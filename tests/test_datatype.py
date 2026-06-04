"""BillType / BillItem / BillItemStatus 的单元测试."""

from __future__ import annotations

import pytest

from shmtu_cas import (
    BillItem,
    BillItemStatus,
    BillType,
    sum_money,
)


class TestBillType:
    def test_tab_no_values(self) -> None:
        assert BillType.ALL.tab_no == "1"
        assert BillType.SUCCESS.tab_no == "2"
        assert BillType.NOT_PAID.tab_no == "3"
        assert BillType.FAILURE.tab_no == "4"

    def test_description_chinese(self) -> None:
        assert BillType.ALL.description == "全部"
        assert BillType.SUCCESS.description == "成功"
        assert BillType.NOT_PAID.description == "未付款"
        assert BillType.FAILURE.description == "失败"

    def test_parse_case_insensitive(self) -> None:
        assert BillType.parse("ALL") is BillType.ALL
        assert BillType.parse("success") is BillType.SUCCESS
        assert BillType.parse("NotPaid") is BillType.NOT_PAID

    def test_parse_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="未知的 BillType"):
            BillType.parse("bogus")

    def test_str(self) -> None:
        assert str(BillType.ALL) == "全部"


def _make_single(timestamp: int, number: str, money: float) -> BillItem:
    return BillItem.new_single(
        date_str="2026.05.21",
        time_str="123045",
        time_str_formatted="12:30:45",
        date_time_formatted="2026.05.21 12:30:45",
        timestamp=timestamp,
        item_type="消费",
        number=number,
        target_user="食堂",
        money_str=f"{money:.2f}",
        money=money,
        method="刷卡",
        status_str="交易成功",
    )


class TestBillItem:
    def test_new_single_basic(self) -> None:
        item = _make_single(100, "N001", 10.0)
        assert item.number == "N001"
        assert item.number_list == ["N001"]
        assert item.is_combined is False
        assert item.timestamp == 100
        assert item.end_timestamp == 100

    def test_equality_by_number_list(self) -> None:
        a = _make_single(100, "N001", 10.0)
        b = _make_single(200, "N001", 20.0)  # 同 number, 不同时间/金额
        assert a == b  # equality 基于 number_list

    def test_inequality_different_number(self) -> None:
        a = _make_single(100, "N001", 10.0)
        b = _make_single(100, "N002", 10.0)
        assert a != b

    def test_merge_two(self) -> None:
        a = _make_single(100, "N001", 10.0)
        b = _make_single(200, "N002", 20.0)
        merged = BillItem.merge([a, b])
        assert merged.is_combined
        assert merged.number == ""
        assert merged.number_list == ["N001", "N002"]
        assert abs(merged.money - 30.0) < 1e-6
        assert merged.timestamp == 100
        assert merged.end_timestamp == 200

    def test_merge_single_returns_clone(self) -> None:
        a = _make_single(100, "N001", 10.0)
        merged = BillItem.merge([a])
        assert not merged.is_combined
        assert merged == a

    def test_merge_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="不能合并"):
            BillItem.merge([])

    def test_merge_with_helper(self) -> None:
        a = _make_single(100, "N001", 10.0)
        b = _make_single(200, "N002", 20.0)
        merged = a.merge_with(b)
        assert merged.is_combined
        assert len(merged.number_list) == 2

    def test_status_recognized(self) -> None:
        item = _make_single(100, "N001", 10.0)
        assert item.status() is BillItemStatus.SUCCESS

    def test_status_unknown_returns_all(self) -> None:
        item = _make_single(100, "N001", 10.0)
        item.status_str = "未知状态"
        assert item.status() is BillItemStatus.ALL

    def test_get_field_csv(self) -> None:
        a = _make_single(100, "N001", 10.0)
        assert a.get_field("date_str") == "2026.05.21"
        assert a.get_field("time_str") == "123045"
        assert a.get_field("money") == "10.00"
        assert a.get_field("is_combined") == "False"
        assert a.get_field("status") == "交易成功"
        assert a.get_field("unknown") == ""

    def test_str_single(self) -> None:
        a = _make_single(100, "N001", 10.0)
        s = str(a)
        assert "消费" in s
        assert "合并" not in s

    def test_str_combined(self) -> None:
        a = _make_single(100, "N001", 10.0)
        b = _make_single(200, "N002", 20.0)
        merged = BillItem.merge([a, b])
        s = str(merged)
        assert "2条合并" in s
        assert " - " in s


class TestBillItemStatus:
    def test_from_text(self) -> None:
        assert BillItemStatus.from_text("交易成功") is BillItemStatus.SUCCESS
        assert BillItemStatus.from_text("#all") is BillItemStatus.ALL
        assert BillItemStatus.from_text("#waitfor") is BillItemStatus.WAITFOR
        assert BillItemStatus.from_text("#fail") is BillItemStatus.FAILURE
        assert BillItemStatus.from_text("随便") is None


def test_sum_money() -> None:
    items = [_make_single(100, "N001", 10.0), _make_single(200, "N002", 20.5)]
    assert abs(sum_money(items) - 30.5) < 1e-6
