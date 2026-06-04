# EpayAuth

> 版本：1.0.0

一卡通充值平台（`https://ecard.shmtu.edu.cn`）认证客户端。**三阶段设计 + Cookie 持久化**。

## 构造

```python
EpayAuth(
    captcha_resolver: CaptchaResolver | None = None,
    *,
    client: httpx.AsyncClient | None = None,
)
```

异步上下文：

```python
async with EpayAuth() as epay:
    ...
```

## 三阶段登录

```python
probe: LoginProbe = await epay.probe_login()
if not probe.is_already_logged_in:
    challenge: LoginChallenge = await epay.prepare_challenge()
    answer = await resolver.resolve(challenge.captcha_image)  # 由业务方选择 resolver
    result: LoginSubmitResult = await epay.submit_login(
        username="20210000",
        password="your_password",
        validate_code=answer.into_final_answer(),
        execution=challenge.execution,
    )
    if not result.is_success:
        print(result.variant, result.message)
```

## 一键登录

```python
result = await epay.submit_login_auto("20210000", "your_password", max_retries=5)
```

内部循环：`probe_login` → `prepare_challenge` → `resolver.resolve` → `submit_login`；连续失败重试至 `max_retries`，仍失败则抛 `ManualCaptchaRequiredException`。

## 拉账单

```python
html: str = await epay.get_bill(page_no=1, tab_no="1")
```

## 会话持久化

```python
# 导出
blob = epay.extract_session()
with open("session.json", "w") as f:
    f.write(blob)

# 恢复
with open("session.json") as f:
    epay.restore_session(f.read())

# 拼到 httpx 请求
cookie_str = epay.get_cookie_string()
```

## TGC 复用

```python
ok: bool = await epay.try_reuse_tgc()
if not ok:
    # TGC 已失效，需要重新登录
    ...
```
