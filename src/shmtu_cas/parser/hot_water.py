"""热水 HTML 解析 — 对齐 Rust ``parser/hot_water.rs`` 与 Kotlin ``parser/HotWaterParser``."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

UL_SELECTOR = "#tab1 > div > div > ul"
LI_SELECTOR = "li"
DIV_BAGREEN_SELECTOR = "div.bagreen"
DIGIT_RE = re.compile(r"\d+")


@dataclass
class HotWaterInfo:
    """单条热水信息 — 对齐 Rust ``HotWaterInfo``."""

    building: int
    temperature: float
    water_level: float  # 百分比


def _only_digits(s: str) -> str:
    return "".join(DIGIT_RE.findall(s))


def _only_float_digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit() or c == ".")


def parse_hot_water_list(html: str) -> list[HotWaterInfo]:
    """解析热水 HTML, 返回 ``[(温度, 水位%, 楼号), ...]``.

    对齐 Rust ``parser::parse_hot_water_list`` 与 Kotlin ``HotWaterParser.getHotWaterList``.
    """
    document = BeautifulSoup(html, "lxml")
    result: list[HotWaterInfo] = []

    ul = document.select_one(UL_SELECTOR)
    if ul is None:
        return result

    for li in ul.select(LI_SELECTOR):
        div = li.select_one(DIV_BAGREEN_SELECTOR)
        if div is None:
            continue
        children = [c for c in div.children if isinstance(c, Tag)]
        if len(children) != 3:
            continue

        temp_text = _only_float_digits(children[0].get_text().replace("℃", ""))
        level_text = _only_float_digits(
            children[1].get_text().replace("水位", "").replace("%", "")
        )
        building_text = _only_digits(children[2].get_text())

        try:
            temperature = float(temp_text)
            water_level = float(level_text)
            building = int(building_text)
        except ValueError:
            continue

        result.append(
            HotWaterInfo(building=building, temperature=temperature, water_level=water_level)
        )
    return result
