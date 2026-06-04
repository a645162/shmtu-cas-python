"""登录会话共享的 dataclass — 跨 Epay/Wechat 复用."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class LoginChallenge:
    """一次登录尝试所需的材料 — 对齐 Rust ``LoginChallenge``.

    ``prepare_challenge()`` 返回; 流程在此暂停, 由调用方决定如何处理验证码图片.
    """

    execution: str
    captcha_image: bytes


@dataclass(frozen=True)
class LoginProbe:
    """探测登录状态的结果.

    - ``AlreadyLoggedIn``: 已经登录
    - ``NeedLogin(login_url)``: 需要登录, 给的 ``login_url`` 是 CAS 重定向地址
    """

    variant: str
    login_url: str = ""

    @classmethod
    def already_logged_in(cls) -> LoginProbe:
        return cls(variant="already_logged_in")

    @classmethod
    def need_login(cls, login_url: str) -> LoginProbe:
        return cls(variant="need_login", login_url=login_url)

    @property
    def is_need_login(self) -> bool:
        return self.variant == "need_login"

    @property
    def is_already_logged_in(self) -> bool:
        return self.variant == "already_logged_in"


# SessionProbe 是 Kotlin 风格的别名 (sealed class 拆解为单一 dataclass + variant 字段)
SessionProbe = LoginProbe


@dataclass(frozen=True)
class LoginSubmitResult:
    """提交登录后的结果 — 对齐 Rust/Kotlin 同名结构.

    - ``Success``: 登录成功
    - ``ValidateCodeError``: 验证码错误
    - ``PasswordError``: 密码错误
    - ``Failure(message)``: 其他失败
    """

    variant: str
    message: str = ""

    @classmethod
    def success(cls) -> LoginSubmitResult:
        return cls(variant="success")

    @classmethod
    def validate_code_error(cls) -> LoginSubmitResult:
        return cls(variant="validate_code_error")

    @classmethod
    def password_error(cls) -> LoginSubmitResult:
        return cls(variant="password_error")

    @classmethod
    def failure(cls, message: str) -> LoginSubmitResult:
        return cls(variant="failure", message=message)

    @property
    def is_success(self) -> bool:
        return self.variant == "success"

    @property
    def is_validate_code_error(self) -> bool:
        return self.variant == "validate_code_error"

    @property
    def is_password_error(self) -> bool:
        return self.variant == "password_error"

    @property
    def is_failure(self) -> bool:
        return self.variant == "failure"


LoginResultLike = Union[LoginSubmitResult, LoginProbe]
