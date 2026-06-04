# 典型用例

> 版本：1.0.0 | 更新日期：2026-06-04

6 个端到端示例覆盖最常见的库使用场景。

## 索引

| 用例 | 说明 |
| --- | --- |
| [手动验证码 + 拉账单 + 导出](/examples/manual-captcha) | `input()` 输入 + `parse_bill_page` + `CsvExporter` |
| [HTTP OCR 自动登录](/examples/http-ocr) | `OcrHttpCaptchaResolver` + `submit_login_auto` |
| [增量同步（单账号）](/examples/incremental) | `incremental_sync` + `SyncOptions.incremental(MONTH)` |
| [多账号并行同步](/examples/parallel) | `sync_accounts_parallel` + `AccountSyncJob` |
| [本地 ONNX 自定义 Resolver](/examples/local-onnx) | 自定义 `CaptchaResolver` + `onnxruntime` |
| [账单分类 + 位置翻译](/examples/classifier) | `BillClassifier` + `PositionTranslator` |
