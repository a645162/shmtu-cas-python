"""账单数据类型 (对齐 Rust: datatype/bill/* 与 Kotlin: datatype/BillItem)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from .status import BillItemStatus


class BillType(Enum):
    """账单类型 — 对齐 Rust ``BillType`` 与 Kotlin ``BillType``.

    ``tab_no`` 字段直接对应一卡通充值平台 URL 的 ``tabNo`` 参数.
    """

    ALL = "all"
    NOT_PAID = "not_paid"
    SUCCESS = "success"
    FAILURE = "failure"

    @property
    def description(self) -> str:
        """中文标签."""
        match self:
            case BillType.ALL:
                return "全部"
            case BillType.NOT_PAID:
                return "未付款"
            case BillType.SUCCESS:
                return "成功"
            case BillType.FAILURE:
                return "失败"

    @property
    def tab_no(self) -> str:
        """URL ``tabNo`` 参数值 — 对齐 Rust ``BillType::tab_no``."""
        match self:
            case BillType.ALL:
                return "1"
            case BillType.SUCCESS:
                return "2"
            case BillType.NOT_PAID:
                return "3"
            case BillType.FAILURE:
                return "4"

    @classmethod
    def parse(cls, s: str) -> BillType:
        """大小写不敏感解析; 找不到抛 ``ValueError``.

        对齐 Rust ``FromStr for BillType``.
        """
        normalized = s.strip().lower()
        match normalized:
            case "all":
                return cls.ALL
            case "notpaid" | "waitfor" | "not_paid":
                return cls.NOT_PAID
            case "success":
                return cls.SUCCESS
            case "failure" | "fail":
                return cls.FAILURE
        msg = f"未知的 BillType: {s}"
        raise ValueError(msg)

    def __str__(self) -> str:
        return self.description


@dataclass
class BillItem:
    """单条 / 合并账单.

    字段完全对齐 Rust ``BillItem``.  与 Kotlin 的精简版相比, 多了合并账单
    相关的字段 (``end_*`` / ``number_list`` / ``is_combined``).
    """

    # === 时间 ===
    date_str: str
    time_str: str
    time_str_formatted: str
    date_time_formatted: str
    end_date_time_formatted: str
    timestamp: int
    end_timestamp: int

    # === 交易信息 ===
    item_type: str
    number: str
    number_list: list[str] = field(default_factory=list)
    target_user: str = ""

    # === 金额 ===
    money_str: str = "0.00"
    money: float = 0.0

    # === 其他 ===
    method: str = ""
    status_str: str = ""
    is_combined: bool = False

    @classmethod
    def new_single(
        cls,
        *,
        date_str: str,
        time_str: str,
        time_str_formatted: str,
        date_time_formatted: str,
        timestamp: int,
        item_type: str,
        number: str,
        target_user: str,
        money_str: str,
        money: float,
        method: str,
        status_str: str,
    ) -> Self:
        """创建一条原始账单 (非合并)."""
        return cls(
            date_str=date_str,
            time_str=time_str,
            time_str_formatted=time_str_formatted,
            date_time_formatted=date_time_formatted,
            end_date_time_formatted=date_time_formatted,
            timestamp=timestamp,
            end_timestamp=timestamp,
            item_type=item_type,
            number=number,
            number_list=[number],
            target_user=target_user,
            money_str=money_str,
            money=money,
            method=method,
            status_str=status_str,
            is_combined=False,
        )

    def merge_with(self, other: BillItem) -> BillItem:
        """与另一条账单合并."""
        return BillItem.merge([self, other])

    @staticmethod
    def merge(items: list[BillItem]) -> BillItem:
        """合并多条账单, 按时间升序, 金额求和.

        对齐 Rust ``BillItem::merge``.  0 条抛 ``ValueError``,
        1 条直接返回克隆.
        """
        if not items:
            msg = "不能合并空的账单列表"
            raise ValueError(msg)
        if len(items) == 1:
            one = items[0]
            return BillItem(**{**one.__dict__, "number_list": list(one.number_list)})

        sorted_items = sorted(items, key=lambda b: b.timestamp)
        first = sorted_items[0]
        last = sorted_items[-1]
        total_money = sum(b.money for b in sorted_items)
        all_numbers: list[str] = []
        for b in sorted_items:
            all_numbers.extend(b.number_list)

        return BillItem(
            date_str=first.date_str,
            time_str=first.time_str,
            time_str_formatted=first.time_str_formatted,
            date_time_formatted=first.date_time_formatted,
            end_date_time_formatted=last.end_date_time_formatted,
            timestamp=first.timestamp,
            end_timestamp=last.end_timestamp,
            item_type=first.item_type,
            number="",
            number_list=all_numbers,
            target_user=first.target_user,
            money_str=f"{total_money:.2f}",
            money=total_money,
            method=first.method,
            status_str=first.status_str,
            is_combined=True,
        )

    def status(self) -> BillItemStatus:
        """从 ``status_str`` 反解 ``BillItemStatus``; 未识别返回 ``ALL``.

        对齐 Rust ``BillItem::status``.
        """
        from .status import BillItemStatus  # 避免循环导入

        return BillItemStatus.from_text(self.status_str) or BillItemStatus.ALL

    def get_field(self, field_name: str) -> str:
        """CSV 导出按字段名取值. 对齐 Rust ``BillItem::get_field``."""
        match field_name:
            case "date_str":
                return self.date_str
            case "time_str":
                return self.time_str
            case "time_str_formatted":
                return self.time_str_formatted
            case "date_time_formatted":
                return self.date_time_formatted
            case "end_date_time_formatted":
                return self.end_date_time_formatted
            case "timestamp":
                return str(self.timestamp)
            case "end_timestamp":
                return str(self.end_timestamp)
            case "item_type":
                return self.item_type
            case "number":
                return self.number
            case "number_list":
                return ",".join(self.number_list)
            case "target_user":
                return self.target_user
            case "money_str":
                return self.money_str
            case "money":
                return f"{self.money:.2f}"
            case "method":
                return self.method
            case "status" | "status_str":
                return self.status_str
            case "is_combined":
                return str(self.is_combined)
            case _:
                return ""

    def __eq__(self, other: object) -> bool:
        """基于 ``number_list`` 比较 — 对齐 Rust ``PartialEq for BillItem``."""
        if not isinstance(other, BillItem):
            return NotImplemented
        return self.number_list == other.number_list

    def __hash__(self) -> int:
        return hash(tuple(self.number_list))

    def __str__(self) -> str:
        if self.is_combined:
            return (
                f"{self.date_time_formatted} - {self.end_date_time_formatted} | "
                f"{self.item_type} | {self.money:.2f} | "
                f"[{len(self.number_list)}条合并]"
            )
        return (
            f"{self.date_time_formatted} | {self.item_type} | "
            f"{self.target_user} | {self.money_str} | {self.status_str}"
        )


def sum_money(items: list[BillItem]) -> float:
    """对一组账单求金额总和 — 对齐 Rust ``sum_money``."""
    return sum(b.money for b in items)
