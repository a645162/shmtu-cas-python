# WechatAuth

> 版本：1.0.0

微信充值通道认证客户端（与 `EpayAuth` 共享 `CasAuth.create_client()`）。

## 构造

```python
WechatAuth(*, client: httpx.AsyncClient | None = None)
```

## 方法

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `probe_login` | `async () -> LoginProbe` | 探测是否已登录 |
| `get_bill` | `async (page_no, tab_no) -> str` | 拉取微信账单 HTML |

## 用法

```python
from shmtu_cas import WechatAuth

async with WechatAuth() as wx:
    probe = await wx.probe_login()
    if probe.is_already_logged_in:
        html = await wx.get_bill(page_no=1, tab_no="1")
```
