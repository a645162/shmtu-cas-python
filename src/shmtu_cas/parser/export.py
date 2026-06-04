"""CSV 导出 — 对齐 Rust ``parser/export.rs`` 与 Kotlin ``parser/CsvExporter``.

Python 用标准库 ``csv`` 实现, 不依赖第三方 CSV 库.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Iterable

from ..datatype.bill import BillItem

DEFAULT_HEADERS: list[str] = [
    "日期",
    "时间",
    "时间(格式化)",
    "日期时间",
    "时间戳",
    "交易名称",
    "交易号",
    "对方",
    "金额",
    "付款方式",
    "状态",
]

DEFAULT_FIELDS: list[str] = [
    "date_str",
    "time_str",
    "time_str_formatted",
    "date_time_formatted",
    "timestamp",
    "item_type",
    "number",
    "target_user",
    "money_str",
    "method",
    "status",
]


class CsvExporter:
    """账单 CSV 导出器.

    Usage::

        exporter = CsvExporter()
        exporter.export("bills.csv", bills)
        # 或只生成字符串
        text = exporter.to_csv_string(bills)
    """

    def __init__(
        self,
        headers: list[str] | None = None,
        fields: list[str] | None = None,
    ) -> None:
        self.headers: list[str] = headers if headers is not None else list(DEFAULT_HEADERS)
        self.fields: list[str] = fields if fields is not None else list(DEFAULT_FIELDS)

    def with_headers(self, headers: list[str]) -> CsvExporter:
        self.headers = headers
        return self

    def with_fields(self, fields: list[str]) -> CsvExporter:
        self.fields = fields
        return self

    def to_csv_string(self, bills: Iterable[BillItem]) -> str:
        """将账单列表序列化为 CSV 字符串."""
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(self.headers)
        for bill in bills:
            writer.writerow([bill.get_field(f) for f in self.fields])
        return buf.getvalue()

    def export(self, path: str | Path, bills: Iterable[BillItem]) -> None:
        """将账单列表写入 CSV 文件."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(self.headers)
            for bill in bills:
                writer.writerow([bill.get_field(field) for field in self.fields])
