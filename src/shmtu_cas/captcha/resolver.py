"""验证码解析器集合 — 对齐 Rust ``captcha/*resolver`` 与 Kotlin ``CaptchaResolver``."""

from __future__ import annotations

import asyncio
import socket
from typing import Awaitable, Callable, Protocol, runtime_checkable

from .answer import CaptchaAnswer, CaptchaAnswerKind
from .http_ocr import CaptchaOcrHttp
from .tcp_ocr import CaptchaOcr
from .utils import get_expr_result


@runtime_checkable
class CaptchaResolver(Protocol):
    """验证码解析器抽象 — 对齐 Rust ``CaptchaResolver`` trait.

    接收验证码图片字节, 返回 ``CaptchaAnswer``.  默认实现均为 ``async``;
    同步实现可直接返回已 resolved 的协程 (``asyncio.coroutine`` 风格).
    """

    async def resolve(self, image_data: bytes) -> CaptchaAnswer:  # pragma: no cover - protocol
        ...


# === 同步 handler 适配器: 将 ``Callable[[bytes], ...]`` 提升为 async resolver ===

ResolverHandler = Callable[[bytes], CaptchaAnswer | str]
AsyncResolverHandler = Callable[[bytes], Awaitable[CaptchaAnswer | str]]


async def _call_handler(
    handler: ResolverHandler | AsyncResolverHandler, image_data: bytes
) -> CaptchaAnswer:
    result = handler(image_data)
    if asyncio.iscoroutine(result):
        result = await result  # type: ignore[assignment]
    if isinstance(result, CaptchaAnswer):
        return result
    # 字符串返回值: 视为完整算式, 包成 EXPRESSION 形式, 让调用方按需 into_final_answer()
    return CaptchaAnswer(value=str(result), kind=CaptchaAnswerKind.EXPRESSION)


class ManualCaptchaResolver:
    """把验证码图片交给用户/外部回调拿到答案 — 对齐 Rust ``ManualCaptchaResolver``.

    Usage::

        async def ask_user(image: bytes) -> CaptchaAnswer:
            ...  # 保存图片、UI 弹窗、等待输入
            return CaptchaAnswer.answer(user_input)

        resolver = ManualCaptchaResolver(ask_user)
    """

    def __init__(self, handler: ResolverHandler | AsyncResolverHandler) -> None:
        self._handler = handler

    async def resolve(self, image_data: bytes) -> CaptchaAnswer:
        return await _call_handler(self._handler, image_data)


class ExprCaptchaResolver:
    """由调用方提供的"算式"识别函数 — 对齐 Rust ``ExprCaptchaResolver``.

    ``expr_provider`` 返回算式字符串 (e.g. ``"12+34="``), 库内部再取右侧答案.
    """

    def __init__(self, expr_provider: Callable[[bytes], str]) -> None:
        self._expr_provider = expr_provider

    async def resolve(self, image_data: bytes) -> CaptchaAnswer:
        expr = self._expr_provider(image_data)
        return CaptchaAnswer.answer(get_expr_result(expr))


class OcrCaptchaResolver:
    """通过远端 TCP OCR 服务识别 — 对齐 Rust ``OcrCaptchaResolver``.

    同步 OCR 在线程池中执行, 避免阻塞事件循环.
    """

    def __init__(self, ocr: CaptchaOcr, max_retries: int = 3) -> None:
        self._ocr = ocr
        self._max_retries = max_retries

    @classmethod
    def from_host_port(
        cls, host: str, port: int, max_retries: int = 3
    ) -> OcrCaptchaResolver:
        return cls(CaptchaOcr(host=host, port=port), max_retries=max_retries)

    async def resolve(self, image_data: bytes) -> CaptchaAnswer:
        try:
            expr = await asyncio.to_thread(
                self._ocr.ocr_auto_retry, image_data, self._max_retries
            )
        except (ConnectionError, socket.error, OSError) as e:
            msg = f"OCR连接失败: {e}"
            raise RuntimeError(msg) from e
        return CaptchaAnswer.expression(expr)


class OcrHttpCaptchaResolver:
    """通过 RESTful HTTP OCR 服务识别 — 对齐 Rust ``OcrHttpCaptchaResolver``."""

    def __init__(self, ocr: CaptchaOcrHttp, max_retries: int = 3) -> None:
        self._ocr = ocr
        self._max_retries = max_retries

    @classmethod
    def from_base_url(
        cls, base_url: str, max_retries: int = 3
    ) -> OcrHttpCaptchaResolver:
        return cls(CaptchaOcrHttp(base_url=base_url), max_retries=max_retries)

    async def resolve(self, image_data: bytes) -> CaptchaAnswer:
        expr = await self._ocr.ocr_auto_retry_async(image_data, self._max_retries)
        return CaptchaAnswer.expression(expr)


__all__ = [
    "AsyncResolverHandler",
    "CaptchaResolver",
    "ExprCaptchaResolver",
    "ManualCaptchaResolver",
    "OcrCaptchaResolver",
    "OcrHttpCaptchaResolver",
    "ResolverHandler",
]
