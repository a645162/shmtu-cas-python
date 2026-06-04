# shmtu-cas-python — 库参考手册

> 版本：1.0.0 | 更新日期：2026-06-04
>
> 对应 Python 包名：`shmtu-cas`（`import shmtu_cas`）
> GitHub：[HaominKong/shmtu-cas-python](https://github.com/HaominKong/shmtu-cas-python)

---

## 〇、定位与跨语言对照

`shmtu-cas-python` 是上海海事大学 **CAS / 一卡通充值平台 / 热水查询** 的 Python 客户端库。模块细粒度与 `shmtu-cas-rs`（Rust）保持一致，并借鉴 `shmtu-cas-kotlin`（Kotlin 协程）做异步适配。**API 不存在历史包袱**，需要时可直接重写而不考虑兼容。

| 子包 | 对齐 Rust | 对齐 Kotlin | 说明 |
| --- | --- | --- | --- |
| `shmtu_cas.datatype` | `datatype/*` | `datatype/*` | `BillItem` / `BillType` / `BillItemStatus` |
| `shmtu_cas.auth` | `cas/*` | `auth/*` | `EpayAuth` / `WechatAuth` / `CasAuth` / `CookieManager` |
| `shmtu_cas.session` | `cas::{LoginProbe, LoginChallenge, LoginSubmitResult}` | `session/*` | 会话状态 dataclass + 异常 |
| `shmtu_cas.captcha` | `captcha/*` | `captcha/*` | 4 种 `CaptchaResolver` + TCP / HTTP OCR 客户端 |
| `shmtu_cas.parser` | `parser/*` | `parser/*` | 账单 / 热水 HTML 解析 + CSV 导出 |
| `shmtu_cas.classifier` | `classifier/*` | `classifier/*` | `BillClassifier` / `PositionTranslator` |
| `shmtu_cas.sync` | `sync/*` | `sync/*` | 增量同步 + 多账号并行 + 状态机回调 |
| `shmtu_cas.cli` | `cli/*` | — | 命令行入口 `shmtu-cas` |

### 跨语言技术栈映射

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

---

## 一、安装与运行

### 1.1 系统要求

- Python ≥ 3.10
- 运行时依赖：`httpx >= 0.27`, `beautifulsoup4 >= 4.12`, `lxml >= 5.0`
- 可选 OCR 服务：参见聚合仓库 `Server/shmtu-cas-ocr-server` 或 `Model/shmtu-cas-ocr-model`

### 1.2 从 PyPI 安装

```bash
pip install shmtu-cas
```

### 1.3 源码可编辑安装（开发模式）

```bash
git clone https://github.com/HaominKong/shmtu-cas-python.git
cd shmtu-cas-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

`[dev]` 额外包含：`pytest`, `pytest-asyncio`, `mypy`, `ruff`。

### 1.4 在聚合仓库内使用

```bash
# 在 shmtu-terminal 根目录
pip install -e .
pip install -e ./Lib/shmtu-cas-python
```

安装后提供 CLI 入口：`shmtu-cas`（等价于 `python -m shmtu_cas.cli`）。

---

## 二、模块详解

### 2.1 `shmtu_cas.datatype` — 数据类型

#### `BillType` (Enum)

账单类型，对齐 Rust `BillType` 与 Kotlin `BillType`。

| 成员 | 中文 | 解析关键字 |
| --- | --- | --- |
| `INCOME` | 收入 | "收入" / "充值" / "退款" |
| `EXPENSE` | 支出 | "支出" / "消费" / "扣款" |
| `UNKNOWN` | 未知 | fallback |

`BillType.parse(raw_str: str) -> BillType` —— 从原始字符串反解类型。

#### `BillItem` (dataclass)

一条账单的不可变记录，**所有合并 / 求和操作不会修改原对象**。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `date_str` | `str` | 日期字符串（原始格式 `YYYY.MM.DD`） |
| `time_str` | `str` | 时间字符串（原始 `HHMMSS`） |
| `timestamp` | `int` | Unix 秒（用于增量同步） |
| `item_type` | `str` | 交易名称（"食堂消费"、"微信充值"） |
| `number` | `str` | 交易号 |
| `target_user` | `str` | 对方账户 / 位置 |
| `money_str` | `str` | 金额字符串（原始） |
| `money` | `float` | 金额数值（**正=收入，负=支出**） |
| `method` | `str` | 支付方式 |
| `is_combined` | `bool` | 是否为合并记录 |
| `account_id` | `str` | 所属学号 |

`sum_money(items: Iterable[BillItem]) -> float` —— 累加求和（**不可变**，返回新值）。

#### `BillItemStatus` (dataclass)

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `str` | 原始状态码 |
| `is_success` | `bool` | 是否成功 |
| `is_pending` | `bool` | 是否处理中 |
| `is_failed` | `bool` | 是否失败 |

`BillItemStatus.parse(raw: str) -> BillItemStatus` —— 反解。

### 2.2 `shmtu_cas.auth` — 认证

#### `CasAuth`（静态工具类）

通用 CAS 静态门面：

```python
CasAuth.create_client() -> httpx.AsyncClient     # 默认 follow_redirects=False
CasAuth.get_execution_async(client, url, cookie_str) -> tuple[str, str]
cas_login(client, url, payload) -> httpx.Response
cas_redirect(client, url) -> str
build_client() -> httpx.AsyncClient
```

#### `CookieManager`

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `restore` | `(json_str: str) -> None` | 从 JSON 恢复 |
| `extract` | `() -> str` | 导出为 JSON |
| `get` | `() -> str` | 导出 `k=v; k=v` 字符串 |
| `set_cookie` | `(name, value) -> None` | 单点更新 |
| `clear` | `() -> None` | 清空 |

#### `EpayAuth`（核心）

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

#### `WechatAuth`

微信充值通道（与 `EpayAuth` 共享 `CasAuth.create_client()`）。

```python
WechatAuth(*, client: httpx.AsyncClient | None = None)
```

| 方法 | 说明 |
| --- | --- |
| `async probe_login() -> LoginProbe` | 探测 |
| `async get_bill(page_no, tab_no) -> str` | 拉取微信账单 HTML |

#### `cas_login` / `cas_redirect` / `get_execution`

低阶函数，可在自定义认证流程中直接使用。

### 2.3 `shmtu_cas.session` — 会话状态

#### `LoginProbe`

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

#### `LoginChallenge`

```python
@dataclass
class LoginChallenge:
    execution: str       # CAS 一次性 token
    captcha_image: bytes  # PNG/JPEG 原始字节
```

#### `LoginSubmitResult`

```python
@dataclass
class LoginSubmitResult:
    is_success: bool
    variant: str         # "success" / "captcha_error" / "credentials_error" / "server_error" / ...
    message: str
    cookies: dict[str, str]
```

#### `SessionProbe` / `ManualCaptchaRequiredException`

`SessionProbe` 是 `LoginProbe` 的别名。`ManualCaptchaRequiredException` 在 `submit_login_auto` 多次 OCR 失败仍需人工兜底时抛出。

### 2.4 `shmtu_cas.captcha` — 验证码

#### `CaptchaResolver` (Protocol)

```python
@runtime_checkable
class CaptchaResolver(Protocol):
    async def resolve(self, image_data: bytes) -> CaptchaAnswer: ...
```

#### `CaptchaAnswer`

```python
@dataclass
class CaptchaAnswer:
    value: str
    kind: CaptchaAnswerKind   # ANSWER | EXPRESSION

class CaptchaAnswerKind(Enum):
    ANSWER = "answer"            # 直接答案 "42"
    EXPRESSION = "expression"    # 算式 "12+30=" (库内取右侧)
```

#### 4 种 Resolver

| 类 | 用途 | 构造 |
| --- | --- | --- |
| `ManualCaptchaResolver(handler)` | 业务层弹出 UI / 终端输入 | 传 `Callable[[bytes], CaptchaAnswer \| str]` 或异步版 |
| `ExprCaptchaResolver(expr_provider)` | 调用方已有"算式识别"函数 | 传 `Callable[[bytes], str]` |
| `OcrCaptchaResolver(ocr, max_retries=3)` | TCP 远端 OCR | `from_host_port(host, port, max_retries)` |
| `OcrHttpCaptchaResolver(client, endpoint_url, max_retries=3)` | HTTP 远端 OCR | `from_base_url("http://127.0.0.1:21600")` |

自定义 Resolver 示例：

```python
class MyResolver:
    async def resolve(self, image_data: bytes) -> CaptchaAnswer:
        text = await my_model.predict(image_data)
        return CaptchaAnswer.answer(text)
```

#### `CaptchaOcr` (TCP)

```python
CaptchaOcr(host="127.0.0.1", port=21600, timeout=5.0)
  .ocr(image_data)                       # 同步
  .ocr_auto_retry(image_data, max_retries=3)   # 内部重试
```

#### `CaptchaOcrHttp` (HTTP)

```python
CaptchaOcrHttp(client=httpx.AsyncClient(), endpoint_url="http://127.0.0.1:21600/api/ocr")
  .ocr(image_data) -> str
  .ocr_expression(image_data) -> str
```

#### 工具函数

- `fetch_captcha(url, client) -> bytes` —— 下载验证码图片
- `get_expr_result(expr: str) -> str` —— 解析 "12+34=" → "46"

### 2.5 `shmtu_cas.parser` — 解析器

#### 账单 HTML

```python
parse_bill_page(html: str) -> BillParseResult
parse_bill_list(html: str) -> list[BillItem]
parse_bill_item(tr_element) -> BillItem
get_total_pages(html: str) -> int
```

`BillParseResult`:

```python
@dataclass
class BillParseResult:
    bills: list[BillItem]
    total_pages: int
    page_no: int
    tab_no: str
```

#### 热水 HTML

```python
parse_hot_water_list(html: str) -> list[HotWaterInfo]
```

`HotWaterInfo`:

```python
@dataclass
class HotWaterInfo:
    date: str
    time: str
    place: str
    amount: float
    balance: float
```

#### CSV 导出

```python
exporter = CsvExporter()
exporter.export("bills.csv", bills)              # 自动 UTF-8 BOM (Excel 友好)
exporter.export("bills.csv", bills, encoding="utf-8")
```

### 2.6 `shmtu_cas.classifier` — 分类与翻译

#### `BillClassifier`

```python
BillClassifier.from_json(json_str)   # 或 .from_dict(dict)
BillClassifier(rules: list[CategoryRule])
classifier.classify(item_name: str, target: str = "") -> BillCategory
```

`BillCategory` (Enum)：`DEPOSIT` / `BATH` / `CANTEEN` / `SHOPPING` / `TRANSPORT` / `OTHER` / `UNKNOWN`。

`CategoryRule` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `category` | `BillCategory` | 目标分类 |
| `name_keywords` | `list[str]` | 交易名包含 |
| `target_keywords` | `list[str]` | target_user 包含 |
| `priority` | `int` | 匹配优先级（越大越优先） |

#### `PositionTranslator`

把 `海馨楼食堂-1F` 拆为 `(position='海馨楼', room='海馨第1食堂')`。

```python
PositionTranslator.from_json(json_str)   # JSON 含 field + keywords
translator.translate(raw: str) -> PositionEntry | None
```

`PositionEntry`:

```python
@dataclass
class PositionEntry:
    position: str    # 大楼
    room: str        # 房间/楼层
```

### 2.7 `shmtu_cas.sync` — 同步引擎

#### 状态机

```python
class SyncStatusKind(Enum):
    PROBING_LOGIN    = "probing_login"
    GETTING_CAPTCHA  = "getting_captcha"
    LOGGING_IN       = "logging_in"
    SYNCING          = "syncing"
    PERSISTING       = "persisting"
    COMPLETED        = "completed"
    FAILED           = "failed"
```

`SyncStatus` dataclass：`{kind, page, total_pages, error}`。

#### `SyncRangePreset` (Enum)

| 成员 | 起始时间 |
| --- | --- |
| `WEEK` | 7 天前 |
| `HALF_MONTH` | 15 天前 |
| `MONTH` | 30 天前 |
| `HALF_YEAR` | 183 天前 |
| `YEAR` | 365 天前 |
| `ALL` | 无限制 |

`since_timestamp() -> int | None` —— 返回 epoch 秒。

#### `SyncOptions`

```python
@dataclass
class SyncOptions:
    start_page: int = 1
    max_pages: int = 50
    range_start_ts: int | None = None
    stop_on_known_timestamp: int | None = None
    early_stop: bool = True

SyncOptions.incremental(SyncRangePreset.MONTH)  # 工厂
SyncOptions.full()
```

#### `BillStore` / `IncrementalBillStore`

`BillStore` (Protocol)：

```python
class BillStore(Protocol):
    def has_timestamp(self, ts: int) -> bool: ...
    def record(self, bill: BillItem) -> None: ...
    def all_timestamps(self) -> set[int]: ...
```

`IncrementalBillStore` 是默认内存实现（`set[int]`）。

#### 同步入口

```python
async def incremental_sync(
    epay: EpayAuth, store: BillStore, options: SyncOptions,
    *, on_progress: Callable[[SyncPageProgress], None | Awaitable[None]] = None,
) -> SyncResult

async def full_sync(...) -> SyncResult

async def sync_account(job: AccountSyncJob, on_progress=...) -> AccountSyncResult

async def sync_accounts_parallel(
    jobs: list[AccountSyncJob], on_progress=...,
    *, max_concurrency: int | None = None,
) -> ParallelSyncSummary
```

`SyncResult`:

```python
@dataclass
class SyncResult:
    new_bills: list[BillItem]
    new_count: int
    pages_fetched: int
    early_stopped: bool
    duration_ms: int
    status: SyncStatus
```

`ParallelSyncSummary`:

```python
@dataclass
class ParallelSyncSummary:
    success_count: int
    failure_count: int
    total_new_count: int
    per_account: list[AccountSyncResult]
```

#### `AccountSyncJob`

```python
@dataclass
class AccountSyncJob:
    context: AccountContext                # account_label + 描述
    auth: EpayAuth                         # 每个账号独立 auth 实例
    store: BillStore
    options: SyncOptions = SyncOptions.incremental(SyncRangePreset.MONTH)
```

### 2.8 `shmtu_cas.cli` — 命令行

```bash
shmtu-cas --help
shmtu-cas version
shmtu-cas captcha --url http://127.0.0.1:21600/api/ocr --image captcha.png
```

CLI 是 `pyproject.toml` 暴露的 `[project.scripts]` 入口 `shmtu_cas.cli:main`。

---

## 三、典型用例

### 3.1 手动输入验证码 + 拉账单 + 导出 CSV

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

### 3.2 远程 HTTP OCR 自动登录

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

### 3.3 增量同步（单账号）

```python
import asyncio
from shmtu_cas import (
    EpayAuth, IncrementalBillStore,
    SyncOptions, SyncRangePreset, incremental_sync,
)

async def main():
    async with EpayAuth() as epay:
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

### 3.4 多账号并行同步

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
            auth=EpayAuth(),
            store=IncrementalBillStore(),
        )

    jobs = [make_account("acc1"), make_account("acc2")]

    async def on_progress(p):
        print(p.to_message())

    summary = await sync_accounts_parallel(jobs, on_progress=on_progress)
    print(f"汇总: 成功 {summary.success_count}, 失败 {summary.failure_count}, 新增 {summary.total_new_count}")

asyncio.run(main())
```

### 3.5 自定义本地 ONNX Resolver

```python
import asyncio
from shmtu_cas import EpayAuth, CaptchaAnswer

class LocalOnnxResolver:
    def __init__(self, model_path: str):
        import onnxruntime as ort
        self.session = ort.InferenceSession(model_path)

    async def resolve(self, image_data: bytes) -> CaptchaAnswer:
        import numpy as np
        arr = np.frombuffer(image_data, dtype=np.uint8)
        # ... 预处理 + 推理 ...
        text = self.session.run(None, { ... })[0][0]
        return CaptchaAnswer.answer(text)

async def main():
    resolver = LocalOnnxResolver("captcha.onnx")
    async with EpayAuth(captcha_resolver=resolver) as epay:
        result = await epay.submit_login_auto("20210000", "pwd", max_retries=3)
        print(result.variant)
```

### 3.6 账单分类 + 位置翻译

```python
from shmtu_cas import BillClassifier, PositionTranslator

classifier = BillClassifier.from_json("""
{
  "deposit": {"name": ["中行云充值"]},
  "bath":    {"target": ["淋浴", "热水"]},
  "canteen": {"target": ["食堂", "餐厅"]}
}
""")

print(classifier.classify("中行云充值", "商户"))   # BillCategory.DEPOSIT

translator = PositionTranslator.from_json("""
{
  "field": "target",
  "keywords": {
    "海馨楼食堂": {"position": "海馨楼", "room": "海馨第1食堂"}
  }
}
""")
print(translator.translate("海馨楼食堂-1F"))
# PositionEntry(position='海馨楼', room='海馨第1食堂')
```

---

## 四、异步设计要点

- **HTTP 客户端**：`httpx.AsyncClient`，默认 `follow_redirects=False`，与 Rust `reqwest::Client::builder().redirect(Policy::none())` 行为一致。所有 redirect 由业务层显式处理。
- **Cookie 管理**：`CookieManager` 同时支持 JSON 持久化与内存中的 `k=v; k=v` 字符串，对齐 Rust `cas/epay.rs::CookieJar` 与 Kotlin `CookieManager`。
- **Captcha Resolver**：全部为 `async def resolve(image_data: bytes) -> CaptchaAnswer`。自定义 resolver 直接 `await`，无需考虑线程池。
- **Sync 状态机**：`SyncStatus` 携带 `kind` 枚举，与 Kotlin `sealed class SyncStatus` 同构。回调签名 `Callable[[SyncProgress], None | Awaitable[None]]`。
- **早停策略**：`early_stop=True` 时同步引擎会在收到已知时间戳后立即停止翻页，避免无谓请求。

---

## 五、运行测试

```bash
pip install -e ".[dev]"
PYTHONPATH=src pytest tests/ -v
```

测试套件覆盖（**54 / 54 全部通过**）：

| 文件 | 用例数 | 覆盖范围 |
| --- | --- | --- |
| `test_datatype.py` | 17 | `BillType.parse` / `BillItem` 合并 / `BillItemStatus` 状态反解 |
| `test_captcha.py` | 11 | 算式解析 / `ExprCaptchaResolver` / `ManualCaptchaResolver` (sync + async) |
| `test_classifier.py` | 9 | 分类规则匹配 / 位置翻译精确+模糊匹配 |
| `test_parser.py` | 9 | 账单 HTML 解析 / 热水 HTML 解析 / CSV 导出 |
| `test_sync.py` | 4 | 增量同步 / 早停 / 进度回调 / 多账号并行汇总 |
| `test_auth_flow.py` | 4 | 登录三阶段 / Cookie 持久化 / TGC 复用 |

---

## 六、项目结构

```
shmtu-cas-python/
├── pyproject.toml
├── README.md
├── Documents/
│   └── REFERENCE.md          # 本文档
├── src/
│   └── shmtu_cas/
│       ├── __init__.py              # 公共 API re-export
│       ├── datatype/                # BillItem / BillType / BillItemStatus
│       ├── auth/                    # EpayAuth / WechatAuth / CasAuth / CookieManager
│       ├── session/                 # 登录状态 dataclass + ManualCaptchaRequiredException
│       ├── captcha/                 # 4 种 Resolver + TCP/HTTP OCR 客户端
│       ├── parser/                  # HTML 解析 (账单/热水) + CSV 导出
│       ├── classifier/              # BillClassifier + PositionTranslator
│       ├── sync/                    # 同步状态机 + 增量/全量/并行
│       └── cli/                     # 命令行入口
└── tests/                           # 54 个单元测试
```

---

## 七、License

MIT
