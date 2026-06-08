"""一卡通个人账户页解析 — 对齐 Kotlin ``parser/PersonAccountParser``.

对应 ``/epay/personaccount/index`` 接口的 HTML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


def guess_gender_from_id_number(id_number: str) -> str:
    """根据身份证号第 17 位推断性别: 奇数=男性, 偶数=女性, 否则返回空字符串."""
    if len(id_number) < 17:
        return ""
    ch = id_number[16]
    if not ch.isdigit():
        return ""
    digit = int(ch)
    if digit % 2 == 1:
        return "男性"
    return "女性"


@dataclass
class PersonAccountInfo:
    """一卡通个人账户页解析结果.

    资金&安全信息:
        cash_balance / cash_balance_raw / security_question_status / register_date

    基本信息:
        student_id / real_name / gender / fixed_line / id_type / id_number
        email / nickname / class_name / phone_num / remark / user_type

    头部:
        real_name / real_name_auth_status

    CSRF:
        csrf_token / csrf_header
    """

    # 头部
    real_name: str = ""
    real_name_auth_status: str = ""

    # 资金&安全信息
    cash_balance: float = 0.0
    cash_balance_raw: str = ""
    security_question_status: str = ""
    register_date: str = ""

    # 基本信息
    student_id: str = ""
    email: str = ""
    nickname: str = ""
    gender: str = ""
    class_name: str = ""
    phone_num: str = ""
    gender_from_id: str = ""
    id_type: str = ""
    id_number: str = ""
    remark: str = ""
    user_type: str = ""

    # CSRF
    csrf_token: str = ""
    csrf_header: str = "X-CSRF-TOKEN"


# 选择器
_BASEINFO_TBODIES = "#baseinfo tbody"
_PANEL_TITLE = ".panel-title"
_CSRF_META = "meta[name=_csrf]"
_CSRF_HEADER_META = "meta[name=_csrf_header]"

_TD_SELECTOR = "td"
_TBODY_SELECTOR = "tbody"

# panel-title 解析正则: "姓名：xxx 实名认证:已认证" / "姓名:xxx 实名认证:xxx"
_NAME_RE = re.compile(r"姓名[:：]\s*(\S+)")
_AUTH_RE = re.compile(r"实名认证[:：]\s*(\S+)")


def _strip_trailing_colon(text: str) -> str:
    """去除字段名末尾的中英文冒号."""
    return text.rstrip(":：").strip()


def _parse_kv_tbody(tbody) -> dict[str, str]:
    """从单个 ``<tbody>`` 中抽取"字段: 值"形式的键值对, 重复 key 会被后值覆盖."""
    result: dict[str, str] = {}
    if tbody is None:
        return result
    for tr in tbody.find_all("tr"):
        tds = tr.find_all(_TD_SELECTOR)
        if len(tds) < 2:
            continue
        key = _strip_trailing_colon(tds[0].get_text())
        value = tds[1].get_text(strip=True)
        if key:
            result[key] = value
    return result


def _parse_otherinfo_tables(panel) -> dict[str, str]:
    """``#otherinfo`` 下有两张表 (资金信息 + 安全信息), 需要合并所有 tbody."""
    if panel is None:
        return {}
    merged: dict[str, str] = {}
    for tbody in panel.find_all(_TBODY_SELECTOR):
        merged.update(_parse_kv_tbody(tbody))
    return merged


def parse_person_account(html: str) -> PersonAccountInfo:
    """一次性解析整个 HTML 页面."""
    document = BeautifulSoup(html, "lxml")

    # 1) panel-title 标题: 姓名:xxx 实名认证:已认证
    title_text = ""
    title_el = document.select_one(_PANEL_TITLE)
    if title_el is not None:
        title_text = title_el.get_text(separator=" ", strip=True)
    name_match = _NAME_RE.search(title_text)
    auth_match = _AUTH_RE.search(title_text)
    real_name = name_match.group(1) if name_match else ""
    real_name_auth_status = auth_match.group(1) if auth_match else ""

    # 2) CSRF token
    csrf_meta = document.select_one(_CSRF_META)
    csrf_header_meta = document.select_one(_CSRF_HEADER_META)
    csrf_token = csrf_meta.get("content", "") if csrf_meta is not None else ""
    csrf_header = (
        csrf_header_meta.get("content", "X-CSRF-TOKEN")
        if csrf_header_meta is not None
        else "X-CSRF-TOKEN"
    )

    # 3) 基本信息表 (#baseinfo tbody)
    base_info_map = _parse_kv_tbody(document.select_one(_BASEINFO_TBODIES))

    # 4) 资金&安全信息表 (#otherinfo 下两张 table, 各一个 tbody, 合并)
    other_info_map = _parse_otherinfo_tables(document.select_one("#otherinfo"))

    # 资金
    cash_balance_raw = other_info_map.get("现金资金", "").replace("元", "").strip()
    try:
        cash_balance = float(cash_balance_raw)
    except (TypeError, ValueError):
        cash_balance = 0.0

    return PersonAccountInfo(
        real_name=real_name,
        real_name_auth_status=real_name_auth_status,
        cash_balance=cash_balance,
        cash_balance_raw=cash_balance_raw,
        security_question_status=other_info_map.get("安全保护问题", ""),
        register_date=other_info_map.get("注册时间", ""),
        student_id=base_info_map.get("学工号", ""),
        email=base_info_map.get("电子邮箱", ""),
        nickname=base_info_map.get("昵称", ""),
        gender=base_info_map.get("性别", ""),
        class_name=base_info_map.get("班级", ""),
        # 一卡通页面 "手机" 字段常空, 真实手机号放在 "固话" 字段
        # phone_num 兼容: 优先取 "手机", 若为空则用 "固话" 的值
        phone_num=base_info_map.get("手机", "")
        or base_info_map.get("固话", ""),
        gender_from_id=guess_gender_from_id_number(
            base_info_map.get("证件号码", "")
        ),
        id_type=base_info_map.get("证件类型", ""),
        id_number=base_info_map.get("证件号码", ""),
        remark=base_info_map.get("备注", ""),
        user_type=base_info_map.get("用户类型", ""),
        csrf_token=csrf_token,
        csrf_header=csrf_header,
    )


def person_account_to_dict(info: PersonAccountInfo) -> dict[str, object]:
    """序列化为 dict (便于 JSON 导出)."""
    return {
        "real_name": info.real_name,
        "real_name_auth_status": info.real_name_auth_status,
        "cash_balance": info.cash_balance,
        "cash_balance_raw": info.cash_balance_raw,
        "security_question_status": info.security_question_status,
        "register_date": info.register_date,
        "student_id": info.student_id,
        "email": info.email,
        "nickname": info.nickname,
        "gender": info.gender,
        "class_name": info.class_name,
        "phone_num": info.phone_num,
        "gender_from_id": info.gender_from_id,
        "id_type": info.id_type,
        "id_number": info.id_number,
        "remark": info.remark,
        "user_type": info.user_type,
        "csrf_token": info.csrf_token,
        "csrf_header": info.csrf_header,
    }


__all__ = [
    "PersonAccountInfo",
    "parse_person_account",
    "person_account_to_dict",
]
