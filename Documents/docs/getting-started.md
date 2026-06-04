# 快速开始

> 版本：1.0.0 | 更新日期：2026-06-04

## 系统要求

- Python ≥ 3.10
- 运行时依赖：`httpx >= 0.27`, `beautifulsoup4 >= 4.12`, `lxml >= 5.0`
- 可选 OCR 服务：参见 `Server/shmtu-cas-ocr-server` 或 `Model/shmtu-cas-ocr-model`

## 从 PyPI 安装

```bash
pip install shmtu-cas
```

## 源码可编辑安装（开发模式）

```bash
git clone https://github.com/a645162/shmtu-cas-python.git
cd shmtu-cas-python
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

`[dev]` 额外包含：`pytest`, `pytest-asyncio`, `mypy`, `ruff`。

## 在聚合仓库内使用

```bash
# 在 shmtu-terminal 根目录
pip install -e .
pip install -e ./Lib/shmtu-cas-python
```

安装后提供 CLI 入口：`shmtu-cas`（等价于 `python -m shmtu_cas.cli`）。

## Hello, 登录

```python
import asyncio
from shmtu_cas import EpayAuth, LoginChallenge

async def main():
    async with EpayAuth() as epay:
        probe = await epay.probe_login()
        if probe.is_already_logged_in:
            print("已登录, 直接拉账单")
            html = await epay.get_bill(page_no=1, tab_no="1")
            print(f"账单 HTML 长度: {len(html)}")
        else:
            challenge: LoginChallenge = await epay.prepare_challenge()
            validate_code = input(f"请输入验证码 (execution={challenge.execution[:8]}...): ")
            result = await epay.submit_login(
                username="20210000",
                password="your_password",
                validate_code=validate_code,
                execution=challenge.execution,
            )
            print("登录结果:", result.variant, result.message)

asyncio.run(main())
```

## 下一步

- [API 索引](/api-overview) — 公共 API 一览
- [典型用例](/examples/index) — 6 个端到端示例
- [跨语言对照](/cross-language) — 与 Rust / Kotlin 实现对应关系
