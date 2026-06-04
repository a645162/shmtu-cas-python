# 异步设计要点

> 版本：1.0.0 | 更新日期：2026-06-04

- **HTTP 客户端**：`httpx.AsyncClient`，默认 `follow_redirects=False`，与 Rust `reqwest::Client::builder().redirect(Policy::none())` 行为一致。所有 redirect 由业务层显式处理。
- **Cookie 管理**：`CookieManager` 同时支持 JSON 持久化与内存中的 `k=v; k=v` 字符串，对齐 Rust `cas/epay.rs::CookieJar` 与 Kotlin `CookieManager`。
- **Captcha Resolver**：全部为 `async def resolve(image_data: bytes) -> CaptchaAnswer`。自定义 resolver 直接 `await`，无需考虑线程池。
- **Sync 状态机**：`SyncStatus` 携带 `kind` 枚举，与 Kotlin `sealed class SyncStatus` 同构。回调签名 `Callable[[SyncProgress], None | Awaitable[None]]`。
- **早停策略**：`early_stop=True` 时同步引擎会在收到已知时间戳后立即停止翻页，避免无谓请求。
