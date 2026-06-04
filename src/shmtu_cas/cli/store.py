"""基于 JSON 文件的 ``BillStore`` 实现 — CLI 同步模式使用."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..datatype.bill import BillItem
from ..sync.engine import BillStore


class JsonBillStore(BillStore):
    """把 ``BillItem`` 列表序列化到本地 JSON 文件, 跨次运行复用.

    行为对齐 Rust ``shmtu-cas-cli`` 的 ``JsonBillStore``.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._bills: list[dict[str, object]] = []
        self._known_numbers: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(data, list):
            return
        self._bills = [b for b in data if isinstance(b, dict)]
        for b in self._bills:
            number = b.get("number")
            if isinstance(number, str) and number:
                self._known_numbers.add(number)

    def save(self) -> None:
        """写回 JSON 文件."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._bills, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # === BillStore 协议 ===
    def contains(self, transaction_no: str) -> bool:
        return transaction_no in self._known_numbers

    def merge(self, new_bills: list[BillItem]) -> None:
        for bill in new_bills:
            if bill.number and bill.number not in self._known_numbers:
                self._known_numbers.add(bill.number)
                self._bills.append(asdict(bill))

    def clear(self) -> None:
        self._bills.clear()
        self._known_numbers.clear()

    def all_bills(self) -> list[dict[str, object]]:
        return list(self._bills)
