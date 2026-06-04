# CookieManager

> 版本：1.0.0

Cookie 持久化 + 序列化工具。

## 方法

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `restore` | `(json_str: str) -> None` | 从 JSON 字符串恢复 |
| `extract` | `() -> str` | 导出为 JSON 字符串 |
| `get` | `() -> str` | 导出 `k=v; k=v` 字符串 |
| `set_cookie` | `(name, value) -> None` | 单点更新（已存在则覆盖） |
| `clear` | `() -> None` | 清空 |

## 用法

```python
from shmtu_cas import CookieManager

mgr = CookieManager()
mgr.set_cookie("TGC", "TGT-abc...")

# 持久化
blob = mgr.extract()
with open("session.json", "w") as f:
    f.write(blob)

# 恢复
with open("session.json") as f:
    mgr.restore(f.read())

# 拼到 httpx 请求
cookie_str = mgr.get()
```
