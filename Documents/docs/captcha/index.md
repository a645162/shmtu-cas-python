# shmtu_cas.captcha — 验证码

> 版本：1.0.0 | 更新日期：2026-06-04

对齐 Rust `captcha/*` 与 Kotlin `captcha/*`。

## CaptchaResolver (Protocol)

```python
@runtime_checkable
class CaptchaResolver(Protocol):
    async def resolve(self, image_data: bytes) -> CaptchaAnswer: ...
```

## CaptchaAnswer

```python
@dataclass
class CaptchaAnswer:
    value: str
    kind: CaptchaAnswerKind   # ANSWER | EXPRESSION

class CaptchaAnswerKind(Enum):
    ANSWER = "answer"            # 直接答案 "42"
    EXPRESSION = "expression"    # 算式 "12+30=" (库内取右侧)
```

## 4 种 Resolver

| 类 | 用途 | 构造 |
| --- | --- | --- |
| `ManualCaptchaResolver(handler)` | 业务层弹出 UI / 终端输入 | 传 `Callable[[bytes], CaptchaAnswer \| str]` 或异步版 |
| `ExprCaptchaResolver(expr_provider)` | 调用方已有"算式识别"函数 | 传 `Callable[[bytes], str]` |
| `OcrCaptchaResolver(ocr, max_retries=3)` | TCP 远端 OCR | `from_host_port(host, port, max_retries)` |
| `OcrHttpCaptchaResolver(client, endpoint_url, max_retries=3)` | HTTP 远端 OCR | `from_base_url("http://127.0.0.1:21600")` |

### 自定义 Resolver 示例

```python
class MyResolver:
    async def resolve(self, image_data: bytes) -> CaptchaAnswer:
        text = await my_model.predict(image_data)
        return CaptchaAnswer.answer(text)
```

## 底层 OCR 客户端

### CaptchaOcr (TCP)

```python
CaptchaOcr(host="127.0.0.1", port=21600, timeout=5.0)
  .ocr(image_data)                       # 同步
  .ocr_auto_retry(image_data, max_retries=3)   # 内部重试
```

### CaptchaOcrHttp (HTTP)

```python
CaptchaOcrHttp(client=httpx.AsyncClient(), endpoint_url="http://127.0.0.1:21600/api/ocr")
  .ocr(image_data) -> str
  .ocr_expression(image_data) -> str
```

## 工具函数

- `fetch_captcha(url, client) -> bytes` —— 下载验证码图片
- `get_expr_result(expr: str) -> str` —— 解析 "12+34=" → "46"

## 子页面

- [CaptchaResolver 协议](/captcha/resolver)
- [4 种内置 Resolver](/captcha/built-in)
- [TCP / HTTP OCR 客户端](/captcha/ocr-clients)
