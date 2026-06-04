# CasAuth

> 版本：1.0.0

通用 CAS 静态门面（不维护状态）。

```python
from shmtu_cas import CasAuth

client = CasAuth.create_client()
```

## 静态方法

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `create_client` | `() -> httpx.AsyncClient` | 默认 `follow_redirects=False` |
| `get_execution_async` | `(client, url, cookie_str) -> tuple[str, str]` | 拉取 CAS 表单 `execution` 与新 cookie |
| `cas_login` | `(client, url, payload) -> httpx.Response` | 提交登录表单 |
| `cas_redirect` | `(client, url) -> str` | 跟随一次重定向并返回最终 URL |
| `build_client` | `() -> httpx.AsyncClient` | 等价 `create_client` |
