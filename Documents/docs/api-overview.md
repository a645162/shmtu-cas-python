# API 索引

> 版本：1.0.0 | 更新日期：2026-06-04

`shmtu_cas` 顶层 `__init__.py` 重新导出下面这些公共符号。完整签名见各子包页面。

## 数据类型

| 符号 | 来自 | 说明 |
| --- | --- | --- |
| `BillType` | `shmtu_cas.datatype` | 账单类型枚举（收入 / 支出 / 未知） |
| `BillItem` | `shmtu_cas.datatype` | 一条账单的不可变记录 |
| `BillItemStatus` | `shmtu_cas.datatype` | 账单状态（成功 / 处理中 / 失败） |
| `HotWaterInfo` | `shmtu_cas.parser` | 一条热水消费记录 |

详见：[datatype/bill-type](/datatype/bill-type)、[datatype/bill-item](/datatype/bill-item)、[datatype/bill-item-status](/datatype/bill-item-status)。

## 认证

| 符号 | 来自 | 说明 |
| --- | --- | --- |
| `CasAuth` | `shmtu_cas.auth` | CAS 静态门面（create_client / get_execution / cas_login / cas_redirect） |
| `CookieManager` | `shmtu_cas.auth` | Cookie JSON 持久化 + k=v 字符串导出 |
| `EpayAuth` | `shmtu_cas.auth` | 一卡通充值平台认证客户端（核心） |
| `WechatAuth` | `shmtu_cas.auth` | 微信充值通道认证客户端 |
| `cas_login` / `cas_redirect` / `get_execution` | `shmtu_cas.auth` | 低阶函数 |

详见：[auth/cas-auth](/auth/cas-auth)、[auth/cookie-manager](/auth/cookie-manager)、[auth/epay-auth](/auth/epay-auth)、[auth/wechat-auth](/auth/wechat-auth)。

## 会话状态

| 符号 | 来自 | 说明 |
| --- | --- | --- |
| `LoginProbe` | `shmtu_cas.session` | 探测结果（已登录 / 需登录） |
| `LoginChallenge` | `shmtu_cas.session` | CAS execution + 验证码字节 |
| `LoginSubmitResult` | `shmtu_cas.session` | 提交登录结果（is_success + variant + cookies） |
| `SessionProbe` | `shmtu_cas.session` | `LoginProbe` 的别名 |
| `ManualCaptchaRequiredException` | `shmtu_cas.session` | 自动 OCR 多次失败后抛出 |

详见：[session/login-states](/session/login-states)、[session/exceptions](/session/exceptions)。

## 验证码

| 符号 | 来自 | 说明 |
| --- | --- | --- |
| `CaptchaResolver` | `shmtu_cas.captcha` | `Protocol`：async def resolve(bytes) -> CaptchaAnswer |
| `CaptchaAnswer` / `CaptchaAnswerKind` | `shmtu_cas.captcha` | 答案封装（ANSWER / EXPRESSION） |
| `ManualCaptchaResolver` | `shmtu_cas.captcha` | 业务层手动输入 |
| `ExprCaptchaResolver` | `shmtu_cas.captcha` | 调用方已有"算式识别"函数 |
| `OcrCaptchaResolver` | `shmtu_cas.captcha` | TCP 远端 OCR |
| `OcrHttpCaptchaResolver` | `shmtu_cas.captcha` | HTTP 远端 OCR |
| `CaptchaOcr` / `CaptchaOcrHttp` | `shmtu_cas.captcha` | 底层 OCR 客户端 |
| `fetch_captcha` / `get_expr_result` | `shmtu_cas.captcha` | 工具函数 |

详见：[captcha/resolver](/captcha/resolver)、[captcha/built-in](/captcha/built-in)、[captcha/ocr-clients](/captcha/ocr-clients)。

## 解析器

| 符号 | 来自 | 说明 |
| --- | --- | --- |
| `parse_bill_page` | `shmtu_cas.parser` | 解析账单 HTML 页（含分页信息） |
| `parse_bill_list` | `shmtu_cas.parser` | 解析账单 HTML 列表 |
| `parse_bill_item` | `shmtu_cas.parser` | 解析单条账单 |
| `get_total_pages` | `shmtu_cas.parser` | 提取总页数 |
| `parse_hot_water_list` | `shmtu_cas.parser` | 解析热水 HTML |
| `CsvExporter` | `shmtu_cas.parser` | CSV 导出（自动 UTF-8 BOM） |

详见：[parser/bill](/parser/bill)、[parser/hot-water](/parser/hot-water)、[parser/csv-export](/parser/csv-export)。

## 分类与翻译

| 符号 | 来自 | 说明 |
| --- | --- | --- |
| `BillClassifier` | `shmtu_cas.classifier` | 按规则对账单分类 |
| `BillCategory` | `shmtu_cas.classifier` | 分类枚举 |
| `CategoryRule` | `shmtu_cas.classifier` | 单条规则 |
| `PositionTranslator` | `shmtu_cas.classifier` | 把 `海馨楼食堂-1F` 拆为 (position, room) |
| `PositionEntry` | `shmtu_cas.classifier` | 翻译结果 |

详见：[classifier/bill-classifier](/classifier/bill-classifier)、[classifier/position-translator](/classifier/position-translator)。

## 同步引擎

| 符号 | 来自 | 说明 |
| --- | --- | --- |
| `SyncStatusKind` / `SyncStatus` | `shmtu_cas.sync` | 状态机枚举与数据类 |
| `SyncRangePreset` | `shmtu_cas.sync` | 起始时间预设 |
| `SyncOptions` | `shmtu_cas.sync` | 同步参数 |
| `BillStore` / `IncrementalBillStore` | `shmtu_cas.sync` | 存储接口与默认实现 |
| `SyncResult` / `ParallelSyncSummary` | `shmtu_cas.sync` | 同步结果 |
| `AccountContext` / `AccountSyncJob` | `shmtu_cas.sync` | 多账号任务 |
| `incremental_sync` / `full_sync` | `shmtu_cas.sync` | 单账号同步入口 |
| `sync_account` / `sync_accounts_parallel` | `shmtu_cas.sync` | 多账号同步入口 |

详见：[sync/state-machine](/sync/state-machine)、[sync/options](/sync/options)、[sync/bill-store](/sync/bill-store)、[sync/entry-points](/sync/entry-points)。

## CLI

| 符号 | 来自 | 说明 |
| --- | --- | --- |
| `shmtu-cas` | `[project.scripts]` | 命令行入口，等价于 `python -m shmtu_cas.cli` |

详见：[cli/index](/cli/index)。
