# HTTP OCR 自动登录

> 版本：1.0.0

```python
import asyncio
from shmtu_cas import EpayAuth, OcrHttpCaptchaResolver

async def main():
    resolver = OcrHttpCaptchaResolver.from_base_url("http://127.0.0.1:21600")
    async with EpayAuth(captcha_resolver=resolver) as epay:
        result = await epay.submit_login_auto(
            username="20210000",
            password="your_password",
            max_retries=5,
        )
        print("登录结果:", result.variant)

asyncio.run(main())
```

需要本地起一个 `Server/shmtu-cas-ocr-server`（默认 21600 端口），或替换为 `OcrCaptchaResolver` 走 TCP 通道。
