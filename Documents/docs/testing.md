# 测试与覆盖率

> 版本：1.0.0

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

## Lint

```bash
ruff check .
```
