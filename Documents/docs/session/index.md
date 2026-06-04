# shmtu_cas.session — 会话状态

> 版本：1.0.0 | 更新日期：2026-06-04

对齐 Rust `cas::{LoginProbe, LoginChallenge, LoginSubmitResult}`。

## LoginProbe

```python
@dataclass
class LoginProbe:
    is_already_logged_in: bool
    login_url: str
    @classmethod
    def already_logged_in(cls) -> "LoginProbe": ...
    @classmethod
    def need_login(cls, url: str) -> "LoginProbe": ...
```

## LoginChallenge

```python
@dataclass
class LoginChallenge:
    execution: str       # CAS 一次性 token
    captcha_image: bytes  # PNG/JPEG 原始字节
```

## LoginSubmitResult

```python
@dataclass
class LoginSubmitResult:
    is_success: bool
    variant: str         # "success" / "captcha_error" / "credentials_error" / "server_error" / ...
    message: str
    cookies: dict[str, str]
```

`variant` 字面量与 Rust / Kotlin 完全相同，跨语言可直接序列化。

## SessionProbe & ManualCaptchaRequiredException

- `SessionProbe` 是 `LoginProbe` 的别名（保持与 Rust `SessionProbe` 命名一致）。
- `ManualCaptchaRequiredException` 在 `submit_login_auto` 多次 OCR 失败仍需人工兜底时抛出。

## 子页面

- [LoginProbe / Challenge / Result](/session/login-states)
- [SessionProbe & Exceptions](/session/exceptions)
