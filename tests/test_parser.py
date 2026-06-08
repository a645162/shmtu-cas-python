"""Parser 单元测试 (bill + hot_water + export + person_account)."""

from __future__ import annotations

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from shmtu_cas import (
    BillItem,
    CsvExporter,
    PersonAccountInfo,
    parse_bill_item,
    parse_bill_list,
    parse_bill_page,
    parse_hot_water_list,
    parse_person_account,
    person_account_to_dict,
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


# =================== person_account ===================


_PERSON_ACCOUNT_FIXTURE_HTML = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="utf-8">
    <meta name="_csrf" content="deadbeef-1234-5678-9abc-def012345678"/>
    <meta name="_csrf_header" content="X-CSRF-TOKEN"/>
    <title>一卡通服务平台 - 账户管理页面</title>
</head>
<body>
    <h4 class="panel-title">姓名：张三 实名认证:已认证</h4>
    <div id="baseinfo" class="tab-pane fade">
        <table><tbody>
            <tr><td>学工号：</td><td>202430500099</td></tr>
            <tr><td>电子邮箱：</td><td>zs@example.com</td></tr>
            <tr><td>真实姓名：</td><td>张三</td></tr>
            <tr><td>昵称：</td><td></td></tr>
            <tr><td>性别：</td><td>女</td></tr>
            <tr><td>班级：</td><td>航运2024-1</td></tr>
            <tr><td>手机：</td><td>13800138000</td></tr>
            <tr><td>固话：</td><td>021-12345678</td></tr>
            <tr><td>证件类型：</td><td>身份证</td></tr>
            <tr><td>证件号码：</td><td>310101199901011234</td></tr>
            <tr><td>备注：</td><td></td></tr>
            <tr><td>用户类型：</td><td>本科生</td></tr>
        </tbody></table>
    </div>
    <div id="otherinfo" class="tab-pane fade in active">
        <table><tbody>
            <tr><td>现金资金：</td><td>123.45 元</td></tr>
        </tbody></table>
        <table><tbody>
            <tr><td>安全保护问题：</td><td>您已经设置安全保护问题</td></tr>
            <tr><td>注册时间：</td><td>2024年09月01日</td></tr>
        </tbody></table>
    </div>
</body>
</html>
"""


def test_parse_person_account_full() -> None:
    """从完整 fixture HTML 解析所有字段, 包括跨 tbody 合并."""
    info = parse_person_account(_PERSON_ACCOUNT_FIXTURE_HTML)
    assert isinstance(info, PersonAccountInfo)

    # 头部
    assert info.real_name == "张三"
    assert info.real_name_auth_status == "已认证"

    # 资金&安全
    assert info.cash_balance_raw == "123.45"
    assert info.cash_balance == pytest.approx(123.45)
    assert info.security_question_status == "您已经设置安全保护问题"
    assert info.register_date == "2024年09月01日"

    # 基本信息
    assert info.student_id == "202430500099"
    assert info.email == "zs@example.com"
    assert info.gender == "女"
    assert info.class_name == "航运2024-1"
    assert info.phone_num == "13800138000"  # "手机" 字段
    # 真实一卡通页面 "手机" 字段常空, 实际手机号在 "固话" 字段
    # 我们的 parser 做了兼容合并: phone_num 优先取 "手机", 为空时取 "固话"
    assert info.id_type == "身份证"
    assert info.id_number == "310101199901011234"
    assert info.user_type == "本科生"

    # CSRF
    assert info.csrf_token == "deadbeef-1234-5678-9abc-def012345678"
    assert info.csrf_header == "X-CSRF-TOKEN"


def test_parse_person_account_merges_otherinfo_tbodies() -> None:
    """验证 #otherinfo 下的多张 table 会被合并到同一 dict (关键回归)."""
    info = parse_person_account(_PERSON_ACCOUNT_FIXTURE_HTML)
    # 如果没有合并, register_date/security_question_status 会是空
    assert info.security_question_status != ""
    assert info.register_date != ""


def test_parse_person_account_empty_html() -> None:
    """空 HTML 应得到所有字段为空的默认值, 不抛异常."""
    info = parse_person_account("<html><body></body></html>")
    assert info.real_name == ""
    assert info.cash_balance == 0.0
    assert info.cash_balance_raw == ""
    assert info.student_id == ""
    assert info.csrf_token == ""


def test_parse_person_account_missing_csrf_header_meta() -> None:
    """若没有 _csrf_header meta, 应当回退到 X-CSRF-TOKEN."""
    html = """
    <html><head>
        <meta name="_csrf" content="abc"/>
    </head><body>
        <h4 class="panel-title">姓名:李四</h4>
    </body></html>
    """
    info = parse_person_account(html)
    assert info.csrf_token == "abc"
    assert info.csrf_header == "X-CSRF-TOKEN"
    assert info.real_name == "李四"


def test_parse_person_account_invalid_cash_balance() -> None:
    """现金资金字段非数字时, 应回退到 0.0, 不抛异常."""
    html = """
    <html><body>
        <div id="otherinfo"><table><tbody>
            <tr><td>现金资金：</td><td>非数字 元</td></tr>
        </tbody></table></div>
    </body></html>
    """
    info = parse_person_account(html)
    assert info.cash_balance_raw == "非数字"
    assert info.cash_balance == 0.0


def test_person_account_to_dict_is_jsonable() -> None:
    """person_account_to_dict 输出必须可被 json.dumps 序列化."""
    import json
    info = parse_person_account(_PERSON_ACCOUNT_FIXTURE_HTML)
    d = person_account_to_dict(info)
    # 不抛异常即视为通过
    json.dumps(d, ensure_ascii=False)
    assert d["student_id"] == "202430500099"
    assert d["cash_balance"] == pytest.approx(123.45)


def test_cli_has_person_account_subcommands() -> None:
    """CLI 必须注册 person-account 与 parse-person-account 子命令."""
    from shmtu_cas.cli.main import build_parser

    parser = build_parser()
    # 解析不应抛 SystemExit
    # person-account 需要 -u/-p, 但 parse_args 不要求强制, 我们只验证 subcommand 注册
    args = parser.parse_args(
        ["person-account", "-u", "test", "-p", "test"]
    )
    assert args.command == "person-account"
    # parse-person-account 也要存在
    args2 = parser.parse_args(
        ["parse-person-account", "-i", "/tmp/x.html"]
    )
    assert args2.command == "parse-person-account"
