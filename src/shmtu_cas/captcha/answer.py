"""验证码答案包装 — 对齐 Rust ``CaptchaAnswer`` / ``CaptchaAnswerKind``."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CaptchaAnswerKind(Enum):
    """答案类型 — 对齐 Rust ``CaptchaAnswerKind``."""

    EXPRESSION = "expression"
    ANSWER = "answer"


@dataclass
class CaptchaAnswer:
    """验证码解析结果.

    OCR 服务可能返回完整算式 (e.g. ``"12+34="``) 或直接给出答案.
    调用 ``into_final_answer()`` 统一规约为最终答案字符串.
    """

    value: str
    kind: CaptchaAnswerKind = CaptchaAnswerKind.EXPRESSION

    @classmethod
    def answer(cls, value: str) -> CaptchaAnswer:
        """构造一个已是最终答案的包装."""
        return cls(value=value, kind=CaptchaAnswerKind.ANSWER)

    @classmethod
    def expression(cls, value: str) -> CaptchaAnswer:
        """构造一个算式 (还需取 ``=`` 右侧)."""
        return cls(value=value, kind=CaptchaAnswerKind.EXPRESSION)

    def into_final_answer(self) -> str:
        """规约为最终答案字符串 — 对齐 Rust ``CaptchaAnswer::into_final_answer``."""
        from .utils import get_expr_result

        if self.kind is CaptchaAnswerKind.ANSWER:
            return self.value
        return get_expr_result(self.value)
