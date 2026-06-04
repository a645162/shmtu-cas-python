"""账单状态枚举 — 对齐 Rust ``BillItemStatus`` 与 Kotlin ``BillItemStatus``."""

from __future__ import annotations

from enum import Enum


class BillItemStatus(Enum):
    """账单条目状态.

    注意: 这里保留 Rust 版的 4 个值, ``ALL`` 表示未识别/全部; 与 Kotlin
    版 ``UNKNOWN`` 同语义但保留 ``ALL`` 命名以与 Rust 保持一致.
    """

    ALL = "all"
    WAITFOR = "waitfor"
    SUCCESS = "success"
    FAILURE = "failure"

    @property
    def description(self) -> str:
        match self:
            case BillItemStatus.ALL:
                return "#all"
            case BillItemStatus.WAITFOR:
                return "#waitfor"
            case BillItemStatus.SUCCESS:
                return "交易成功"
            case BillItemStatus.FAILURE:
                return "#fail"

    @classmethod
    def from_text(cls, text: str) -> BillItemStatus | None:
        """从页面文本反解状态; 找不到返回 ``None``.

        对齐 Rust ``BillItemStatus::from_text``.
        """
        match text.strip():
            case "交易成功":
                return cls.SUCCESS
            case "#all":
                return cls.ALL
            case "#waitfor":
                return cls.WAITFOR
            case "#fail":
                return cls.FAILURE
            case _:
                return None

    def __str__(self) -> str:
        return self.description
