# shmtu_cas.auth — 认证

> 版本：1.0.0 | 更新日期：2026-06-04

对齐 Rust `cas/*` 与 Kotlin `auth/*`。

## CasAuth（静态工具类）

通用 CAS 静态门面：

```python
from shmtu_cas import CasAuth

client = CasAuth.create_client()                 # 默认 follow_redirects=False
execution, cookie_str = await CasAuth.get_execution_async(client, url, cookie_str)
response = await cas_login(client, url, payload)
final_url = await cas_redirect(client, url)
client = CasAuth.build_client()
```

## CookieManager

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `restore` | `(json_str: str) -> None` | 从 JSON 恢复 |
| `extract` | `() -> str` | 导出为 JSON |
| `get` | `() -> str` | 导出 `k=v; k=v` 字符串 |
| `set_cookie` | `(name, value) -> None` | 单点更新 |
| `clear` | `() -> None` | 清空 |

## EpayAuth（核心）

一卡通充值平台（`https://ecard.shmtu.edu.cn`）认证客户端。**三阶段设计 + Cookie 持久化**。

```python
EpayAuth(
    captcha_resolver: CaptchaResolver | None = None,
    *,
    client: httpx.AsyncClient | None = None,
)
```

| 阶段 | 方法 | 返回 |
| --- | --- | --- |
| 1. 探测 | `async probe_login() -> LoginProbe` | 是否已登录 / 跳转 URL |
| 2. 挑战 | `async prepare_challenge() -> LoginChallenge` | execution + 验证码图片字节 |
| 3. 提交 | `async submit_login(username, password, validate_code, execution) -> LoginSubmitResult` | 登录结果 |
| 一键 | `async submit_login_auto(username, password, max_retries=5) -> LoginSubmitResult` | 内部自循环探测+挑战+OCR+提交 |
| 拉账单 | `async get_bill(page_no=1, tab_no="1") -> str` | 账单 HTML |
| 会话 | `restore_session(json_str)` / `extract_session() -> str` / `get_cookie_string() -> str` | 持久化 / 复用 |
| TGC | `async try_reuse_tgc() -> bool` | 检测 TGC 是否有效 |

异步上下文：

```python
async with EpayAuth() as epay:
    ...
```

## WechatAuth

微信充值通道（与 `EpayAuth` 共享 `CasAuth.create_client()`）。

```python
WechatAuth(*, client: httpx.AsyncClient | None = None)
```

| 方法 | 说明 |
| --- | --- |
| `async probe_login() -> LoginProbe` | 探测 |
| `async get_bill(page_no, tab_no) -> str` | 拉取微信账单 HTML |

## 低阶函数

- `cas_login(client, url, payload) -> httpx.Response`
- `cas_redirect(client, url) -> str`
- `get_execution(...)` —— 在自定义认证流程中直接使用

## 子页面

- [CasAuth](/auth/cas-auth)
- [CookieManager](/auth/cookie-manager)
- [EpayAuth](/auth/epay-auth)
- [WechatAuth](/auth/wechat-auth)
