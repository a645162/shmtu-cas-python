"""Classifier 单元测试."""

from __future__ import annotations

import pytest

from shmtu_cas import (
    BillCategory,
    BillClassifier,
    PositionTranslator,
)


class TestBillClassifier:
    def _make(self) -> BillClassifier:
        return BillClassifier.from_json(
            """{
            "deposit": {"name": ["中行云充值", "微信充值"]},
            "bath": {"target": ["淋浴", "热水"]},
            "canteen": {"target": ["食堂", "餐厅"]}
        }"""
        )

    def test_classify_by_name(self) -> None:
        c = self._make()
        assert c.classify("中行云充值", "某商户") is BillCategory.DEPOSIT

    def test_classify_by_target(self) -> None:
        c = self._make()
        assert c.classify("消费", "淋浴") is BillCategory.BATH
        assert c.classify("消费", "海馨食堂") is BillCategory.CANTEEN

    def test_classify_other(self) -> None:
        c = self._make()
        assert c.classify("消费", "未知商户") is BillCategory.OTHER

    def test_display_name(self) -> None:
        assert BillCategory.CANTEEN.display_name == "食堂"
        assert BillCategory.OTHER.display_name == "其他"

    def test_emoji(self) -> None:
        assert BillCategory.CANTEEN.emoji == "🍚"
        assert BillCategory.OTHER.emoji == "💳"

    def test_from_string(self) -> None:
        assert BillCategory.from_string("deposit") is BillCategory.DEPOSIT
        assert BillCategory.from_string("UNKNOWN") is BillCategory.OTHER


class TestPositionTranslator:
    def _make(self) -> PositionTranslator:
        return PositionTranslator.from_json(
            """{
            "field": "target",
            "keywords": {
                "A食堂1楼大餐厅": {"position": "海馨楼", "room": "海馨第1食堂"},
                "淋浴": {"position": "公共浴室", "room": "浴室"},
                "教育超市": {"position": "校园商业", "room": "教育超市"}
            }
        }"""
        )

    def test_exact_match(self) -> None:
        t = self._make()
        result = t.translate("A食堂1楼大餐厅")
        assert result is not None
        assert result.position == "海馨楼"
        assert result.room == "海馨第1食堂"

    def test_fuzzy_match(self) -> None:
        t = self._make()
        result = t.translate("淋浴-北区浴室")
        assert result is not None
        assert result.position == "公共浴室"

    def test_no_match(self) -> None:
        t = self._make()
        assert t.translate("未知地点") is None

    def test_translate_or_raw(self) -> None:
        t = self._make()
        result = t.translate_or_raw("未知地点")
        assert result.position == "未知地点"
        assert result.room == "未知地点"
