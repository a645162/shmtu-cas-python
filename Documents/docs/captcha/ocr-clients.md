# TCP / HTTP OCR 客户端

> 版本：1.0.0

底层 OCR 客户端供高级用户绕过 Resolver 直接调用。

## CaptchaOcr (TCP)

```python
from shmtu_cas import CaptchaOcr

ocr = CaptchaOcr(host="127.0.0.1", port=21600, timeout=5.0)

# 同步调用
text = ocr.ocr(image_data)

# 内部重试
text = ocr.ocr_auto_retry(image_data, max_retries=3)
```

对应 `Server/shmtu-cas-ocr-server` 的 TCP 端口。

## CaptchaOcrHttp (HTTP)

```python
from shmtu_cas import CaptchaOcrHttp
import httpx

client = httpx.AsyncClient()
ocr = CaptchaOcrHttp(client=client, endpoint_url="http://127.0.0.1:21600/api/ocr")

text = ocr.ocr(image_data)
expr = ocr.ocr_expression(image_data)
```

HTTP 接口为 `POST {endpoint_url}` body `{"imageBase64": "..."}`，兼容多种返回结构。

## 工具函数

```python
from shmtu_cas import fetch_captcha, get_expr_result

# 下载验证码图片
img: bytes = await fetch_captcha("https://cas.shmtu.edu.cn/...", client)

# 解析算式
result: str = get_expr_result("12+34=")   # "46"
```
