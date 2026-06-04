"""通过 RESTful HTTP OCR 服务识别验证码 — 对齐 Rust ``captcha::CaptchaOcrHttp``."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class CaptchaOcrHttp:
    """HTTP OCR 客户端.

    协议:
        POST {base_url}/api/ocr  Body: ``{"imageBase64": "<base64>"}``
        Response: ``{"success": bool, "expression": "...", "result": int, "error": "..."}``
    """

    base_url: str
    timeout: float = 10.0
    _client: httpx.AsyncClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> CaptchaOcrHttp:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    @staticmethod
    def _decode(payload: dict[str, Any]) -> str:
        if not payload.get("success"):
            err_msg = payload.get("error") or "未知错误"
            msg = f"RESTful OCR识别失败: {err_msg}"
            raise RuntimeError(msg)
        expression = payload.get("expression")
        if not expression:
            msg = "OCR成功但未返回表达式"
            raise RuntimeError(msg)
        return str(expression)

    async def ocr_by_http(self, image_data: bytes) -> str:
        """单次识别."""
        b64 = base64.b64encode(image_data).decode("ascii")
        body = {"imageBase64": b64}
        try:
            response = await self._client.post(f"{self.base_url}/api/ocr", json=body)
            response.raise_for_status()
        except httpx.HTTPError as e:
            msg = "连接RESTful OCR服务器失败"
            raise RuntimeError(msg) from e
        result = response.json()
        if not isinstance(result, dict):
            msg = "OCR 响应不是 JSON 对象"
            raise RuntimeError(msg)
        return self._decode(result)

    async def ocr_auto_retry_async(self, image_data: bytes, max_retries: int = 3) -> str:
        """带重试的异步 OCR; 失败抛 ``RuntimeError``."""
        last_error: Exception | None = None
        for i in range(max_retries):
            try:
                result = await self.ocr_by_http(image_data)
                if result:
                    return result
                last_error = RuntimeError("OCR返回空结果")
            except Exception as e:  # noqa: BLE001
                last_error = e
                print(f"第{i + 1}次RESTful OCR尝试失败: {e}")
                if i < max_retries - 1:
                    await asyncio.sleep(1)
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"RESTful OCR在{max_retries}次重试后失败")

    async def health_check_async(self) -> bool:
        """异步健康检查 — 探测 ``/api/health`` 返回 2xx 即视为健康."""
        try:
            response = await self._client.get(f"{self.base_url}/api/health")
        except httpx.HTTPError:
            return False
        return response.status_code < 400
