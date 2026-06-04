"""位置翻译器 — 对齐 Rust ``classifier/position.rs`` 与 Kotlin ``classifier/PositionTranslator``."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PositionEntry:
    """位置翻译条目."""

    position: str
    room: str


@dataclass
class PositionTranslator:
    """将 ``target_user`` (对方账户) 翻译为目标名称和房间.

    加载规则: 优先 JSON, 文件名以 ``.toml`` 结尾时尝试解析 TOML.

    Attributes:
        field_name: 规则主字段名 (对齐 Rust 版的 ``field`` 字段).
        keywords: 关键词到位置/房间的映射.
    """

    field_name: str = "target"
    keywords: dict[str, PositionEntry] = field(default_factory=dict)

    @classmethod
    def from_json(cls, json_str: str) -> PositionTranslator:
        data: dict[str, Any] = json.loads(json_str)
        keywords_raw = data.get("keywords", data) if isinstance(data, dict) else {}
        keywords: dict[str, PositionEntry] = {}
        for key, value in keywords_raw.items():
            if isinstance(value, dict):
                keywords[key] = PositionEntry(
                    position=str(value.get("position", "")),
                    room=str(value.get("room", "")),
                )
        return cls(field_name=data.get("field", "target"), keywords=keywords)

    @classmethod
    def from_file(cls, path: str | Path) -> PositionTranslator:
        content = Path(path).read_text(encoding="utf-8")
        path_str = str(path)
        if path_str.endswith(".toml"):
            return cls._from_toml(content)
        return cls.from_json(content)

    @classmethod
    def _from_toml(cls, toml_str: str) -> PositionTranslator:
        """轻量级 TOML 解析: 仅支持 ``[position]`` 与 ``[position.keywords."X"]`` 表.

        复杂格式请使用 ``tomllib`` (Py 3.11+) 或 ``tomli``; 此处为避免额外依赖提供简化实现.
        """
        field_name = "target"
        keywords: dict[str, PositionEntry] = {}
        current_section: str | None = None
        current_kw: str | None = None
        current_building = ""
        current_room = ""
        for raw in toml_str.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                if section == "position":
                    current_section = "position"
                    current_kw = None
                elif section.startswith("position.keywords."):
                    current_section = "position"
                    current_kw = section[len("position.keywords.") :].strip('"')
                continue
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"')
            if current_section == "position" and current_kw is None:
                if k == "field":
                    field_name = v
            elif current_kw is not None:
                if k == "building":
                    current_building = v
                elif k == "room":
                    current_room = v
                    keywords[current_kw] = PositionEntry(
                        position=current_building, room=current_room
                    )
        return cls(field=field_name, keywords=keywords)

    def translate(self, target_user: str) -> PositionEntry | None:
        """翻译 target_user; 找不到返回 None.

        优先精确匹配, 再做模糊包含匹配.
        """
        trimmed = target_user.strip()
        if trimmed in self.keywords:
            return self.keywords[trimmed]
        for keyword, entry in self.keywords.items():
            if keyword in trimmed:
                return entry
        return None

    def translate_or_raw(self, target_user: str) -> PositionEntry:
        """翻译, 找不到则返回 raw."""
        result = self.translate(target_user)
        if result is not None:
            return result
        return PositionEntry(position=target_user, room=target_user)
