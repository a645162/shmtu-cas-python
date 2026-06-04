---
layout: home

hero:
  name: shmtu-cas-python
  text: 库参考手册
  tagline: 上海海事大学 CAS / 一卡通 / 热水查询 的 Python 客户端库
  actions:
    - theme: brand
      text: 快速开始
      link: /getting-started
    - theme: alt
      text: API 索引
      link: /api-overview
    - theme: alt
      text: 典型用例
      link: /examples/index
    - theme: alt
      text: 跨语言对照
      link: /cross-language

features:
  - title: 登录 / 同步 / 识别
    details: EpayAuth 探测 / 挑战 / 提交三阶段；BillStore trait 接入存储；CaptchaResolver 4 种实现
  - title: 模块细粒度
    details: datatype / auth / session / captcha / parser / classifier / sync / cli — 全部为可独立 import 的子包
  - title: 跨语言对齐
    details: 与 shmtu-cas-rs（Rust）和 shmtu-cas-kotlin（Kotlin 协程）保持模块名 / 字段 / 流程同构
  - title: 现代异步栈
    details: httpx.AsyncClient (follow_redirects=False) · beautifulsoup4 + lxml · asyncio · dataclasses
---

## 这是什么

`shmtu-cas-python` 是上海海事大学 **CAS / 一卡通充值平台 / 热水查询** 的 Python 客户端库。模块细粒度与 `shmtu-cas-rs`（Rust）保持一致，并借鉴 `shmtu-cas-kotlin`（Kotlin 协程）做异步适配。**API 不存在历史包袱**，需要时可直接重写而不考虑兼容。

## 子包一览

| 子包 | 对齐 Rust | 说明 |
| --- | --- | --- |
| `shmtu_cas.datatype` | `datatype/*` | `BillItem` / `BillType` / `BillItemStatus` |
| `shmtu_cas.auth` | `cas/*` | `EpayAuth` / `WechatAuth` / `CasAuth` / `CookieManager` |
| `shmtu_cas.session` | `cas::{LoginProbe, LoginChallenge, LoginSubmitResult}` | 会话状态 dataclass + 异常 |
| `shmtu_cas.captcha` | `captcha/*` | 4 种 `CaptchaResolver` + TCP / HTTP OCR 客户端 |
| `shmtu_cas.parser` | `parser/*` | 账单 / 热水 HTML 解析 + CSV 导出 |
| `shmtu_cas.classifier` | `classifier/*` | `BillClassifier` / `PositionTranslator` |
| `shmtu_cas.sync` | `sync/*` | 增量同步 + 多账号并行 + 状态机回调 |
| `shmtu_cas.cli` | `cli/*` | 命令行入口 `shmtu-cas` |

## 最快的上手路径

```python
import asyncio
from shmtu_cas import EpayAuth, OcrHttpCaptchaResolver

async def main():
    resolver = OcrHttpCaptchaResolver.from_base_url("http://127.0.0.1:21600")
    async with EpayAuth(captcha_resolver=resolver) as epay:
        result = await epay.submit_login_auto("20210000", "your_password", max_retries=5)
        print("登录结果:", result.variant)

asyncio.run(main())
```

完整示例参见 [典型用例](/examples/index)。
