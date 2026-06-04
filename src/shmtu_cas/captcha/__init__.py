"""captcha 子包 — 验证码解析器集合 (与 Rust captcha/* 模块对齐)."""

from .answer import CaptchaAnswer, CaptchaAnswerKind
from .http_ocr import CaptchaOcrHttp
from .resolver import (
    CaptchaResolver,
    ExprCaptchaResolver,
    ManualCaptchaResolver,
    OcrCaptchaResolver,
    OcrHttpCaptchaResolver,
)
from .tcp_ocr import CaptchaOcr
from .utils import CAPTCHA_URL, fetch_captcha, get_expr_result

__all__ = [
    "CaptchaAnswer",
    "CaptchaAnswerKind",
    "CaptchaOcr",
    "CaptchaOcrHttp",
    "CaptchaResolver",
    "ExprCaptchaResolver",
    "ManualCaptchaResolver",
    "OcrCaptchaResolver",
    "OcrHttpCaptchaResolver",
    "CAPTCHA_URL",
    "fetch_captcha",
    "get_expr_result",
]
