"""账单分类器 — 对齐 Rust ``classifier/classify.rs`` 与 Kotlin ``classifier/BillClassifier``."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class BillCategory(Enum):
    """账单分类 — 对齐 Rust ``BillCategory`` 与 Kotlin ``BillCategory``."""

    DEPOSIT = "deposit"
    ELECTRICITY = "electricity"
    BATH = "bath"
    HOT_WATER = "hot_water"
    CAKE = "cake"
    CANTEEN = "canteen"
    LIBRARY = "library"
    HOSPITAL = "hospital"
    SHOP = "shop"
    LAUNDRY = "laundry"
    NETWORK = "network"
    TRANSPORT = "transport"
    OTHER = "other"

    @property
    def display_name(self) -> str:
        match self:
            case BillCategory.DEPOSIT:
                return "充值"
            case BillCategory.ELECTRICITY:
                return "电费"
            case BillCategory.BATH:
                return "洗澡"
            case BillCategory.HOT_WATER:
                return "热水"
            case BillCategory.CAKE:
                return "点心"
            case BillCategory.CANTEEN:
                return "食堂"
            case BillCategory.LIBRARY:
                return "图书馆"
            case BillCategory.HOSPITAL:
                return "校医院"
            case BillCategory.SHOP:
                return "超市"
            case BillCategory.LAUNDRY:
                return "洗衣"
            case BillCategory.NETWORK:
                return "网络"
            case BillCategory.TRANSPORT:
                return "交通"
            case BillCategory.OTHER:
                return "其他"

    @property
    def emoji(self) -> str:
        match self:
            case BillCategory.DEPOSIT:
                return "💰"
            case BillCategory.ELECTRICITY:
                return "⚡"
            case BillCategory.BATH:
                return "🚿"
            case BillCategory.HOT_WATER:
                return "♨️"
            case BillCategory.CAKE:
                return "🍰"
            case BillCategory.CANTEEN:
                return "🍚"
            case BillCategory.LIBRARY:
                return "📚"
            case BillCategory.HOSPITAL:
                return "🏥"
            case BillCategory.SHOP:
                return "🛒"
            case BillCategory.LAUNDRY:
                return "👕"
            case BillCategory.NETWORK:
                return "🌐"
            case BillCategory.TRANSPORT:
                return "🚌"
            case BillCategory.OTHER:
                return "💳"

    @classmethod
    def from_string(cls, s: str) -> BillCategory:
        match s.lower():
            case "deposit":
                return cls.DEPOSIT
            case "electricity":
                return cls.ELECTRICITY
            case "bath":
                return cls.BATH
            case "hot_water":
                return cls.HOT_WATER
            case "cake":
                return cls.CAKE
            case "canteen":
                return cls.CANTEEN
            case "library":
                return cls.LIBRARY
            case "hospital":
                return cls.HOSPITAL
            case "shop":
                return cls.SHOP
            case "laundry":
                return cls.LAUNDRY
            case "network":
                return cls.NETWORK
            case "transport":
                return cls.TRANSPORT
            case _:
                return cls.OTHER


@dataclass
class CategoryRule:
    """匹配规则 (按 name 或 target 字段匹配关键词)."""

    name: list[str] = field(default_factory=list)
    target: list[str] = field(default_factory=list)


@dataclass
class BillClassifier:
    """账单分类器 — 对齐 Rust ``BillClassifier`` 与 Kotlin ``BillClassifier``."""

    categories: dict[str, CategoryRule] = field(default_factory=dict)

    @classmethod
    def from_json(cls, json_str: str) -> BillClassifier:
        data: dict[str, Any] = json.loads(json_str)
        categories: dict[str, CategoryRule] = {}
        for cat_name, rule in data.items():
            if isinstance(rule, dict):
                categories[cat_name] = CategoryRule(
                    name=list(rule.get("name", [])),
                    target=list(rule.get("target", [])),
                )
        return cls(categories=categories)

    @classmethod
    def from_file(cls, path: str | Path) -> BillClassifier:
        content = Path(path).read_text(encoding="utf-8")
        return cls.from_json(content)

    def classify(self, name: str, target: str) -> BillCategory:
        """根据 ``name`` / ``target`` 字段分类. 对齐 Rust ``BillClassifier::classify``."""
        for cat_name, rule in self.categories.items():
            for kw in rule.name:
                if kw in name:
                    return BillCategory.from_string(cat_name)
            for kw in rule.target:
                if kw in target:
                    return BillCategory.from_string(cat_name)
        return BillCategory.OTHER
