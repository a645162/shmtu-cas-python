"""手动验证码请求异常 — 对齐 Kotlin ``ManualCaptchaRequiredException``."""

from __future__ import annotations

import base64


class ManualCaptchaRequiredException(Exception):
    """业务层在以下两种情况下抛出本异常:

    1. 手动模式: 调用方探测到需要验证码, 但 ``CaptchaResolver`` 为 null 或未自动处理
    2. 远程 OCR 模式下调用方选择走 UI 兜底

    抛出后 UI 层应弹出验证码输入框, 用户输入后调用 ``submit_login`` 继续流程.
    """

    captcha_image_base64: str
    execution: str
    account_id: str
    account_label: str
    captcha_image_bytes: bytes

    def __init__(
        self,
        *,
        captcha_image_base64: str,
        execution: str,
        account_id: str,
        account_label: str,
        captcha_image_bytes: bytes,
    ) -> None:
        super().__init__("MANUAL_CAPTCHA_REQUIRED")
        self.captcha_image_base64 = captcha_image_base64
        self.execution = execution
        self.account_id = account_id
        self.account_label = account_label
        self.captcha_image_bytes = captcha_image_bytes

    @classmethod
    def of(
        cls,
        *,
        image_bytes: bytes,
        execution: str,
        account_id: str,
        account_label: str,
    ) -> ManualCaptchaRequiredException:
        """从原始图片字节构造, 自动 base64 编码."""
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return cls(
            captcha_image_base64=b64,
            execution=execution,
            account_id=account_id,
            account_label=account_label,
            captcha_image_bytes=image_bytes,
        )
