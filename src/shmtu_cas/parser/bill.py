"""账单 HTML 解析 — 对齐 Rust ``parser/bill/*`` 与 Kotlin ``parser/BillParser``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from ..datatype.bill import BillItem

PAGE_COUNT_RE = re.compile(r"当前\s*(\d+)\s*/\s*(\d+)\s*页")
TR_SELECTOR = "span > table > tbody > tr"
TD_SELECTOR = "td"
DIV_SELECTOR = "div"
PAGE_TD_SELECTOR = "div table td"


@dataclass
class BillParseResult:
    """整页解析结果 — 对齐 Rust ``BillParseResult`` 与 Kotlin ``BillParseResult``."""

    bills: list[BillItem]
    total_pages: int


def get_total_pages(html: str) -> int:
    """从账单页 HTML 提取总页数 (e.g. ``"当前 1/5 页"`` -> 5). 对齐 Rust ``get_total_pages``."""
    document = BeautifulSoup(html, "lxml")
    for td in document.select(PAGE_TD_SELECTOR):
        text = td.get_text()
        match = PAGE_COUNT_RE.search(text)
        if match:
            try:
                return int(match.group(2))
            except ValueError:
                return 1
    return 1


def _extract_text(node: Tag) -> str:
    return node.get_text().strip()


def _format_time(time_str: str) -> str:
    """把 ``123045`` 格式化为 ``12:30:45``."""
    digits = "".join(c for c in time_str if c.isdigit())
    if len(digits) == 6:
        return f"{digits[0:2]}:{digits[2:4]}:{digits[4:6]}"
    return time_str


def _only_digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def _compact_ws(s: str) -> str:
    return " ".join(s.split())


def _split_item_type_and_number(text: str) -> tuple[str, str]:
    """从 ``"水控消费 交易号：20260521135336290726"`` 拆出类型/交易号."""
    idx = text.find("交易号")
    if idx != -1:
        item_type = text[:idx].strip().rstrip(":：").strip()
        number = _only_digits(text[idx:])
        return (item_type, number)
    return (text.strip(), "")


def _parse_deal_cell(cell: Tag) -> tuple[str, str]:
    """解析第 2 列 (交易名称 + 交易号)."""
    divs = cell.select(DIV_SELECTOR)
    if len(divs) >= 2:
        item_type = _compact_ws(_extract_text(divs[0]))
        number = _only_digits(_extract_text(divs[1]))
        if item_type and number:
            return (item_type, number)
    text = _compact_ws(_extract_text(cell))
    return _split_item_type_and_number(text)


def parse_bill_item(row: Tag) -> BillItem | None:
    """解析单行 ``<tr>`` 为 ``BillItem``; 失败返回 ``None``.

    对齐 Rust ``parser::parse_bill_item``.
    """
    tds: list[Tag] = list(row.select(TD_SELECTOR))
    if len(tds) < 6:
        return None

    divs = tds[0].select(DIV_SELECTOR)
    if len(divs) >= 2:
        date_str = _extract_text(divs[0])
        time_str = _extract_text(divs[1])
    else:
        text = _extract_text(tds[0])
        parts = text.split()
        date_str = parts[0] if parts else ""
        time_str = parts[1] if len(parts) > 1 else ""

    time_str_formatted = _format_time(time_str)
    date_time_formatted = f"{date_str} {time_str_formatted}"
    try:
        dt = datetime.strptime(date_time_formatted, "%Y.%m.%d %H:%M:%S")
        timestamp = int(dt.timestamp())
    except ValueError:
        timestamp = 0

    item_type, number = _parse_deal_cell(tds[1])
    target_user = _extract_text(tds[2])
    money_str = _extract_text(tds[3])
    try:
        money = float(money_str)
    except ValueError:
        money = 0.0
    method = _extract_text(tds[4])
    status_str = _extract_text(tds[5])

    return BillItem.new_single(
        date_str=date_str,
        time_str=time_str,
        time_str_formatted=time_str_formatted,
        date_time_formatted=date_time_formatted,
        timestamp=timestamp,
        item_type=item_type,
        number=number,
        target_user=target_user,
        money_str=money_str,
        money=money,
        method=method,
        status_str=status_str,
    )


def parse_bill_list(html: str) -> list[BillItem]:
    """从 HTML 解析出账单列表. 对齐 Rust ``parser::parse_bill_list``."""
    document = BeautifulSoup(html, "lxml")
    bills: list[BillItem] = []
    for row in document.select(TR_SELECTOR):
        item = parse_bill_item(row)  # type: ignore[arg-type]
        if item is not None:
            bills.append(item)
    return bills


def parse_bill_page(html: str) -> BillParseResult:
    """一次性解析整页: 账单条目 + 总页数. 对齐 Rust ``parser::parse_bill_page``."""
    bills = parse_bill_list(html)
    total_pages = get_total_pages(html)
    return BillParseResult(bills=bills, total_pages=total_pages)
