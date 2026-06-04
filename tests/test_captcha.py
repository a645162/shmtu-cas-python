"""Captcha 工具与 Answer 的单元测试."""

from __future__ import annotations

from typing import Any

import pytest

from shmtu_cas import (
    CaptchaAnswer,
    ExprCaptchaResolver,
    ManualCaptchaResolver,
    OcrCaptchaResolver,
    OcrHttpCaptchaResolver,
    get_expr_result,
)
from shmtu_cas.captcha.answer import CaptchaAnswerKind
from shmtu_cas.captcha.http_ocr import CaptchaOcrHttp
from shmtu_cas.captcha.tcp_ocr import CaptchaOcr


class TestGetExprResult:
    @pytest.mark.parametrize(
        ("expr", "expected"),
        [
            ("12+34=46", "46"),
            ("3+5=8", "8"),
            ("10-3=7", "7"),
            ("6*9=54", "54"),
            ("42", "42"),
            (" 12+34=46 ", "46"),
        ],
    )
    def test_expr(self, expr: str, expected: str) -> None:
        assert get_expr_result(expr) == expected


class TestCaptchaAnswer:
    def test_into_final_answer_when_already_answer(self) -> None:
        a = CaptchaAnswer.answer("46")
        assert a.into_final_answer() == "46"

    def test_into_final_answer_when_expression(self) -> None:
        # 对齐 Rust 行为: rfind('=') 之后的空串视为空答案
        a = CaptchaAnswer.expression("12+34=")
        assert a.into_final_answer() == ""
        b = CaptchaAnswer.expression("12+34=46")
        assert b.into_final_answer() == "46"

    def test_kind_defaults_to_expression(self) -> None:
        a = CaptchaAnswer("12+34=")
        assert a.kind is CaptchaAnswerKind.EXPRESSION


class TestExprCaptchaResolver:
    @pytest.mark.asyncio
    async def test_resolve(self) -> None:
        captured: list[bytes] = []

        def provider(image: bytes) -> str:
            captured.append(image)
            return "12+34=46"

        resolver = ExprCaptchaResolver(provider)
        result = await resolver.resolve(b"\x89PNG fake image")
        assert result.into_final_answer() == "46"
        assert captured == [b"\x89PNG fake image"]


class TestManualCaptchaResolver:
    @pytest.mark.asyncio
    async def test_resolve_with_sync_handler(self) -> None:
        def handler(image: bytes) -> CaptchaAnswer:
            return CaptchaAnswer.answer("99")

        resolver = ManualCaptchaResolver(handler)
        result = await resolver.resolve(b"image")
        assert result.into_final_answer() == "99"

    @pytest.mark.asyncio
    async def test_resolve_with_async_handler(self) -> None:
        async def handler(image: bytes) -> CaptchaAnswer:
            return CaptchaAnswer.answer("1234")

        resolver = ManualCaptchaResolver(handler)
        result = await resolver.resolve(b"image")
        assert result.into_final_answer() == "1234"

    @pytest.mark.asyncio
    async def test_resolve_with_str_return(self) -> None:
        def handler(image: bytes) -> str:
            return "12+34=46"

        resolver = ManualCaptchaResolver(handler)
        result = await resolver.resolve(b"image")
        assert result.into_final_answer() == "46"


class TestOcrCaptchaResolver:
    @pytest.mark.asyncio
    async def test_resolve_returns_expression_answer(self) -> None:
        """回归: ``OcrCaptchaResolver.resolve`` 必须返回 ``CaptchaAnswer.expression(...)``.

        之前误写为 ``CaptchaAnswer(expression=...)`` 会触发
        ``TypeError: __init__() got an unexpected keyword argument 'expression'``.
        """

        class _StubOcr:
            def ocr_auto_retry(self, image: bytes, retries: int) -> str:
                return "12+34="

        resolver = OcrCaptchaResolver(_StubOcr(), max_retries=2)  # type: ignore[arg-type]
        result = await resolver.resolve(b"image")
        assert result.kind is CaptchaAnswerKind.EXPRESSION
        assert result.value == "12+34="


class TestOcrHttpCaptchaResolver:
    @pytest.mark.asyncio
    async def test_resolve_returns_expression_answer(self) -> None:
        """回归: ``OcrHttpCaptchaResolver.resolve`` 同样回归."""

        class _StubOcr:
            async def ocr_auto_retry_async(self, image: bytes, retries: int) -> str:
                return "3+5="

        resolver = OcrHttpCaptchaResolver(_StubOcr(), max_retries=2)  # type: ignore[arg-type]
        result = await resolver.resolve(b"image")
        assert result.kind is CaptchaAnswerKind.EXPRESSION
        assert result.value == "3+5="
