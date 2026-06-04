"""Parser 单元测试 (bill + hot_water + export)."""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from shmtu_cas import (
    BillItem,
    CsvExporter,
    parse_bill_item,
    parse_bill_list,
    parse_bill_page,
    parse_hot_water_list,
)


def _make_bill_tr(number: str = "20260521135336290726", money: str = "10.00") -> str:
    return f"""
    <tr>
        <td>
            <div>2026.05.21</div>
            <div>123045</div>
        </td>
        <td>
            <div>水控消费</div>
            <div>交易号: {number}</div>
        </td>
        <td>海馨楼</td>
        <td>{money}</td>
        <td>刷卡</td>
        <td>交易成功</td>
    </tr>
    """


def _wrap(bills_html: str, total_pages: int = 1) -> str:
    return f"""
    <html><body>
        <span><table><tbody>{bills_html}</tbody></table></span>
        <div><table><tbody><tr><td>当前1/{total_pages}页</td></tr></tbody></table></div>
    </body></html>
    """


class TestBillParser:
    def test_parse_bill_item_basic(self) -> None:
        row_html = _make_bill_tr()
        soup = BeautifulSoup(f"<table><tbody>{row_html}</tbody></table>", "lxml")
        row = soup.select_one("tr")
        assert row is not None
        item = parse_bill_item(row)
        assert item is not None
        assert item.date_str == "2026.05.21"
        assert item.time_str == "123045"
        assert item.time_str_formatted == "12:30:45"
        assert item.item_type == "水控消费"
        assert item.number == "20260521135336290726"
        assert item.target_user == "海馨楼"
        assert item.money == 10.0
        assert item.status_str == "交易成功"
        assert item.timestamp > 0

    def test_parse_bill_list(self) -> None:
        html = _wrap(_make_bill_tr("2026052113533629071") + _make_bill_tr("2026052113533629072", "20.50"))
        items = parse_bill_list(html)
        assert len(items) == 2
        assert items[0].number == "2026052113533629071"
        assert items[1].money == 20.5

    def test_parse_bill_page(self) -> None:
        html = _wrap(_make_bill_tr("2026052113533629071"), total_pages=5)
        result = parse_bill_page(html)
        assert result.total_pages == 5
        assert len(result.bills) == 1

    def test_parse_bill_page_default_total(self) -> None:
        html = "<html><body>empty</body></html>"
        result = parse_bill_page(html)
        assert result.total_pages == 1
        assert result.bills == []


class TestHotWaterParser:
    def test_parse_hot_water_list(self) -> None:
        html = """
        <html><body>
            <div id="tab1"><div><div>
                <ul>
                    <li>
                        <div class="bagreen">
                            <div>36.5℃</div>
                            <div>水位75%</div>
                            <div>海馨1号楼</div>
                        </div>
                    </li>
                    <li>
                        <div class="bagreen">
                            <div>42.0℃</div>
                            <div>水位50%</div>
                            <div>海馨2号楼</div>
                        </div>
                    </li>
                    <li>
                        <div>无效条目 (无 bagreen class)</div>
                    </li>
                </ul>
            </div></div></div>
        </body></html>
        """
        result = parse_hot_water_list(html)
        assert len(result) == 2
        assert result[0].temperature == 36.5
        assert result[0].water_level == 75.0
        assert result[0].building == 1  # "海馨1号楼" -> 1

    def test_parse_hot_water_list_empty(self) -> None:
        result = parse_hot_water_list("<html></html>")
        assert result == []


class TestCsvExporter:
    def test_to_csv_string(self) -> None:
        items = [
            BillItem.new_single(
                date_str="2026.05.21",
                time_str="123045",
                time_str_formatted="12:30:45",
                date_time_formatted="2026.05.21 12:30:45",
                timestamp=100,
                item_type="消费",
                number="2026052113533629001",
                target_user="食堂",
                money_str="10.00",
                money=10.0,
                method="刷卡",
                status_str="交易成功",
            )
        ]
        exporter = CsvExporter()
        text = exporter.to_csv_string(items)
        lines = text.strip().split("\n")
        assert len(lines) == 2
        assert "日期" in lines[0]
        assert "2026.05.21" in lines[1]
        assert "2026052113533629001" in lines[1]

    def test_export_to_file(self, tmp_path: Path) -> None:
        items = [
            BillItem.new_single(
                date_str="2026.05.21",
                time_str="123045",
                time_str_formatted="12:30:45",
                date_time_formatted="2026.05.21 12:30:45",
                timestamp=100,
                item_type="消费",
                number="2026052113533629001",
                target_user="食堂",
                money_str="10.00",
                money=10.0,
                method="刷卡",
                status_str="交易成功",
            )
        ]
        exporter = CsvExporter()
        path = tmp_path / "out" / "bills.csv"
        exporter.export(path, items)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "2026052113533629001" in content
