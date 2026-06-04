# shmtu-cas-python

上海海事大学 (SHMTU) **CAS / 一卡通充值平台 / 热水查询** Python 客户端库。

> 该库是 [shmtu-cas-rs](https://github.com/HaominKong/shmtu-terminal/tree/main/shmtu-terminal-tauri/src-tauri/vendor/shmtu-cas-rs) 和 [shmtu-cas-kotlin](https://github.com/HaominKong/shmtu-terminal/tree/main/Server/shmtu-server-unofficial/lib/shmtu-cas-kotlin) 的 Python 移植版, 模块细粒度与 Rust 库保持一致, 并借鉴 Kotlin 库的协程风格做异步适配。

## 安装

```bash
pip install shmtu-cas
```

或从源码安装 (开发模式):

```bash
git clone https://github.com/HaominKong/shmtu-cas-python.git
cd shmtu-cas-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

要求 Python 3.10+.

## 模块概览

| 子包                  | 对齐 Rust           | 对齐 Kotlin                | 说明                          |
| --------------------- | ------------------- | -------------------------- | ----------------------------- |
| `shmtu_cas.datatype`  | `datatype/*`        | `datatype/*`               | `BillItem` / `BillType` / `BillItemStatus` |
| `shmtu_cas.auth`      | `cas/*`             | `auth/*`                   | `EpayAuth` / `WechatAuth` / `CasAuth`       |
| `shmtu_cas.session`   | `cas::{LoginProbe,LoginChallenge,LoginSubmitResult}` | `session/*` | 会话状态 dataclass / 异常                |
| `shmtu_cas.captcha`   | `captcha/*`         | `captcha/*`                | 4 种 Resolver + TCP/HTTP OCR 客户端       |
| `shmtu_cas.parser`    | `parser/*`          | `parser/*`                 | 账单 / 热水 HTML 解析 + CSV 导出           |
| `shmtu_cas.classifier`| `classifier/*`      | `classifier/*`             | `BillClassifier` / `PositionTranslator`    |
| `shmtu_cas.sync`      | `sync/*`            | `sync/*`                   | 增量同步 + 多账号并行 + 状态机回调           |

## 快速上手

### 1. 拉取一卡通账单 (手动输入验证码)

```python
import asyncio
from shmtu_cas import EpayAuth, LoginChallenge, parse_bill_page, CsvExporter

async def main():
    async with EpayAuth() as epay:
        probe = await epay.probe_login()
        if probe.is_already_logged_in:
            html = await epay.get_bill(page_no=1, tab_no="1")
        else:
            challenge: LoginChallenge = await epay.prepare_challenge()
            # ---- 业务层: 把 challenge.captcha_image 展示给用户 ----
            validate_code = input(f"请输入验证码 (execution={challenge.execution[:8]}...): ")

            result = await epay.submit_login(
                username="20210000",
                password="your_password",
                validate_code=validate_code,
                execution=challenge.execution,
            )
            if not result.is_success:
                print("登录失败:", result.variant, result.message)
                return
            html = await epay.get_bill(page_no=1, tab_no="1")

        page = parse_bill_page(html)
        print(f"共 {page.total_pages} 页, 本页 {len(page.bills)} 条")

        exporter = CsvExporter()
        exporter.export("bills.csv", page.bills)

asyncio.run(main())
```

### 2. 远程 OCR 自动登录 (HTTP OCR)

```python
import asyncio
from shmtu_cas import EpayAuth, OcrHttpCaptchaResolver

async def main():
    resolver = OcrHttpCaptchaResolver.from_base_url("http://127.0.0.1:21600")
    async with EpayAuth(captcha_resolver=resolver) as epay:
        result = await epay.submit_login_auto(
            username="20210000",
            password="your_password",
            max_retries=5,
        )
        print("登录结果:", result.variant)

asyncio.run(main())
```

### 3. 增量同步 (单账号)

```python
import asyncio
from shmtu_cas import (
    EpayAuth, IncrementalBillStore,
    SyncOptions, SyncRangePreset, incremental_sync,
)

async def main():
    async with EpayAuth() as epay:
        # 假定已登录
        store = IncrementalBillStore()
        opts = SyncOptions.incremental(SyncRangePreset.MONTH)

        def on_page(p):
            print(f"page {p.page}/{p.total_pages}, new={p.new_count}")

        result = await incremental_sync(epay, store, opts, on_progress=on_page)
        print(f"新增 {result.new_count} 条, 翻 {result.pages_fetched} 页, 早停={result.early_stopped}")
        for bill in result.new_bills:
            print(bill)

asyncio.run(main())
```

### 4. 多账号并行同步

```python
import asyncio
from shmtu_cas import (
    EpayAuth, IncrementalBillStore,
    AccountContext, AccountSyncJob, sync_accounts_parallel,
)

async def main():
    def make_account(label: str) -> AccountSyncJob:
        return AccountSyncJob(
            context=AccountContext(account_label=label),
            auth=EpayAuth(),  # 每个账号独立 auth 实例
            store=IncrementalBillStore(),
        )

    jobs = [make_account("acc1"), make_account("acc2")]

    async def on_progress(p):
        print(p.to_message())

    summary = await sync_accounts_parallel(jobs, on_progress=on_progress)
    print(f"汇总: 成功 {summary.success_count}, 失败 {summary.failure_count}, 新增 {summary.total_new_count}")

asyncio.run(main())
```

### 5. 账单分类 / 位置翻译

```python
from shmtu_cas import BillClassifier, BillCategory, PositionTranslator

classifier = BillClassifier.from_json("""
{
  "deposit": {"name": ["中行云充值"]},
  "bath":    {"target": ["淋浴", "热水"]},
  "canteen": {"target": ["食堂", "餐厅"]}
}
""")

print(classifier.classify("中行云充值", "商户"))  # BillCategory.DEPOSIT

translator = PositionTranslator.from_json("""
{
  "field": "target",
  "keywords": {
    "海馨楼食堂": {"position": "海馨楼", "room": "海馨第1食堂"}
  }
}
""")
print(translator.translate("海馨楼食堂-1F"))  # PositionEntry(position='海馨楼', room='海馨第1食堂')
```

## 异步设计要点

* HTTP 客户端: 使用 `httpx.AsyncClient` (默认 `follow_redirects=False`), 与 Rust `reqwest::Client::builder().redirect(Policy::none())` 行为一致。
* Cookie 管理: `CookieManager` 类同时支持 JSON 持久化与内存中的 `k=v; k=v` 字符串, 与 Rust `cas/epay.rs::CookieJar` / Kotlin `CookieManager` 对齐。
* Captcha Resolver: 全部为 `async def resolve(image_data: bytes) -> CaptchaAnswer`. 自定义 resolver 时直接 `await` 即可, 无需考虑线程池。
* Sync 状态机: `SyncStatus` 携带 `kind` (枚举), 与 Kotlin `sealed class SyncStatus` 同构; 回调签名 `Callable[[SyncProgress], None | Awaitable[None]]`.

## 与 Rust / Kotlin 的差异

| 方面      | Rust                | Kotlin            | Python 移植                   |
| --------- | ------------------- | ----------------- | ----------------------------- |
| HTTP      | `reqwest`           | `okhttp3`         | `httpx`                       |
| HTML 解析 | `scraper`           | `jsoup`           | `beautifulsoup4 + lxml`       |
| 异步      | `tokio`             | `kotlinx.coroutines` | `asyncio`                   |
| 时间戳    | `chrono`            | `java.time`       | `datetime`                    |
| 序列化    | `serde`             | `kotlinx.serialization` | `dataclasses` + `json`     |
| TOML      | `toml`              | —                 | 内置最简实现 (无第三方依赖)     |
| TCP OCR   | `std::net::TcpStream` | `java.net.Socket` | `socket`                    |

## 运行测试

```bash
pip install -e ".[dev]"
PYTHONPATH=src pytest tests/ -v
```

测试套件覆盖:

* `test_datatype.py` (17 cases): `BillType.parse` / `BillItem` 合并 / `BillItemStatus` 状态反解
* `test_captcha.py` (11 cases): 算式解析 / `ExprCaptchaResolver` / `ManualCaptchaResolver` (sync + async)
* `test_classifier.py` (9 cases): 分类规则匹配 / 位置翻译精确+模糊匹配
* `test_parser.py` (9 cases): 账单 HTML 解析 / 热水 HTML 解析 / CSV 导出
* `test_sync.py` (4 cases): 增量同步 / 早停 / 进度回调 / 多账号并行汇总

**当前 54 / 54 全部通过**.

## 项目结构

```
shmtu-cas-python/
├── pyproject.toml
├── README.md
├── src/
│   └── shmtu_cas/
│       ├── __init__.py           # 公共 API 汇总 re-export
│       ├── datatype/              # BillItem / BillType / BillItemStatus
│       ├── auth/                  # EpayAuth / WechatAuth / CasAuth / CookieManager
│       ├── session/               # 登录状态 dataclass + ManualCaptchaRequiredException
│       ├── captcha/               # 4 种 Resolver + TCP/HTTP OCR 客户端
│       ├── parser/                # HTML 解析 (账单/热水) + CSV 导出
│       ├── classifier/            # BillClassifier + PositionTranslator
│       └── sync/                  # 同步状态机 + 增量/全量/并行
└── tests/                         # 54 个单元测试
```

## License

MIT
