# SessionProbe & ManualCaptchaRequiredException

> 版本：1.0.0

## SessionProbe

`SessionProbe` 是 `LoginProbe` 的别名（保持与 Rust `SessionProbe` 命名一致）：

```python
from shmtu_cas import SessionProbe

probe = SessionProbe.already_logged_in()
assert isinstance(probe, LoginProbe)
```

## ManualCaptchaRequiredException

`submit_login_auto` 连续 OCR 失败达 `max_retries` 后抛出。

```python
from shmtu_cas import EpayAuth, ManualCaptchaRequiredException

try:
    result = await epay.submit_login_auto("20210000", "pwd", max_retries=3)
except ManualCaptchaRequiredException as e:
    # 兜底：弹 UI 让用户手动输入
    challenge = await epay.prepare_challenge()
    user_input = ui.prompt_captcha(challenge.captcha_image)
    result = await epay.submit_login("20210000", "pwd", user_input, challenge.execution)
```

业务层捕获此异常后，**应回退到手动验证码流程**（不再继续重试 OCR）。
