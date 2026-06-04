# LoginProbe / LoginChallenge / LoginSubmitResult

> 版本：1.0.0

登录三阶段的状态数据类。

## LoginProbe

探测结果。`EpayAuth.probe_login()` 返回。

```python
from shmtu_cas import LoginProbe

probe = LoginProbe.already_logged_in()
probe = LoginProbe.need_login("https://cas.shmtu.edu.cn/...")

probe.is_already_logged_in   # True / False
probe.login_url              # 跳转或登录 URL
```

## LoginChallenge

挑战响应。`EpayAuth.prepare_challenge()` 返回。

```python
challenge = LoginChallenge(
    execution="e1s1",
    captcha_image=b"\x89PNG\r\n...",  # 原始字节
)
challenge.execution           # str
challenge.captcha_image       # bytes
```

## LoginSubmitResult

提交登录结果。`EpayAuth.submit_login()` / `submit_login_auto()` 返回。

```python
result = LoginSubmitResult(
    is_success=True,
    variant="success",
    message="登录成功",
    cookies={"TGC": "TGT-..."},
)
result.is_success
result.variant        # "success" / "captcha_error" / "credentials_error" / "server_error" / ...
result.message
result.cookies
```

## 典型变体

| variant | 含义 |
| --- | --- |
| `success` | 登录成功 |
| `captcha_error` | 验证码错误（可重试） |
| `credentials_error` | 凭证错误（不应重试） |
| `server_error` | 服务器错误（可重试） |
| `network_error` | 网络错误（可重试） |
