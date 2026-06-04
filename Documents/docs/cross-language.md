# 跨语言对照

> 版本：1.0.0 | 更新日期：2026-06-04

`shmtu-cas-python` 与 `shmtu-cas-rs`（Rust）、`shmtu-cas-kotlin`（Kotlin）保持模块名 / 字段 / 流程同构。

## 模块映射

| 子包（Python） | 对齐 Rust | 对齐 Kotlin | 说明 |
| --- | --- | --- | --- |
| `shmtu_cas.datatype` | `datatype/*` | `datatype/*` | `BillItem` / `BillType` / `BillItemStatus` |
| `shmtu_cas.auth` | `cas/*` | `auth/*` | `EpayAuth` / `WechatAuth` / `CasAuth` / `CookieManager` |
| `shmtu_cas.session` | `cas::{LoginProbe, LoginChallenge, LoginSubmitResult}` | `session/*` | 会话状态 dataclass + 异常 |
| `shmtu_cas.captcha` | `captcha/*` | `captcha/*` | 4 种 `CaptchaResolver` + TCP / HTTP OCR 客户端 |
| `shmtu_cas.parser` | `parser/*` | `parser/*` | 账单 / 热水 HTML 解析 + CSV 导出 |
| `shmtu_cas.classifier` | `classifier/*` | `classifier/*` | `BillClassifier` / `PositionTranslator` |
| `shmtu_cas.sync` | `sync/*` | `sync/*` | 增量同步 + 多账号并行 + 状态机回调 |
| `shmtu_cas.cli` | `cli/*` | — | 命令行入口 `shmtu-cas` |

## 技术栈映射

| 方面 | Rust | Kotlin | Python 移植 |
| --- | --- | --- | --- |
| HTTP 客户端 | `reqwest` | `okhttp3` | `httpx`（默认 `follow_redirects=False`） |
| HTML 解析 | `scraper` | `jsoup` | `beautifulsoup4 + lxml` |
| 异步 | `tokio` | `kotlinx.coroutines` | `asyncio` |
| 时间戳 | `chrono` | `java.time` | `datetime` (UTC) |
| 序列化 | `serde` | `kotlinx.serialization` | `dataclasses` + `json` |
| TOML | `toml` | — | 内置最简实现（无第三方依赖） |
| TCP OCR | `std::net::TcpStream` | `java.net.Socket` | `socket` |
| 重定向策略 | `reqwest::redirect::Policy::none()` | `okhttp` 默认不跟随 | `httpx.AsyncClient(follow_redirects=False)` |

## 设计原则

- **API 不存在历史包袱**：三个语言版本都按"需要时重写"为前提，不保留过时形态
- **模块细粒度一致**：datatype / auth / session / captcha / parser / classifier / sync / cli 在三语都成立
- **异步行为对齐**：Rust `async/await` ↔ Kotlin `suspend` ↔ Python `async def`；Cookie 持久化 / 早停 / 进度回调语义一致
- **统一错误变体**：登录失败 `variant` 字符串（`success` / `captcha_error` / `credentials_error` / `server_error` / ...）在三个语言中使用相同字面量
