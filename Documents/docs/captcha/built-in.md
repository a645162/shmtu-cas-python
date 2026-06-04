# 4 种内置 Resolver

> 版本：1.0.0

| 类 | 用途 | 构造 |
| --- | --- | --- |
| `ManualCaptchaResolver(handler)` | 业务层弹出 UI / 终端输入 | `Callable[[bytes], CaptchaAnswer \| str]` 或异步版 |
| `ExprCaptchaResolver(expr_provider)` | 调用方已有"算式识别"函数 | `Callable[[bytes], str]` |
| `OcrCaptchaResolver(ocr, max_retries=3)` | TCP 远端 OCR | `from_host_port(host, port, max_retries)` |
| `OcrHttpCaptchaResolver(client, endpoint_url, max_retries=3)` | HTTP 远端 OCR | `from_base_url("http://127.0.0.1:21600")` |

## 用法示例

### ManualCaptchaResolver

```python
from shmtu_cas import ManualCaptchaResolver, CaptchaAnswer

def ask_user(image: bytes) -> str:
    # 业务层弹窗 / 终端输入
    return input(f"请输入验证码: ")

resolver = ManualCaptchaResolver(ask_user)
```

### OcrHttpCaptchaResolver（推荐）

```python
from shmtu_cas import OcrHttpCaptchaResolver

resolver = OcrHttpCaptchaResolver.from_base_url("http://127.0.0.1:21600")
```

### ExprCaptchaResolver

```python
from shmtu_cas import ExprCaptchaResolver

def my_ocr(image: bytes) -> str:
    # 返回算式原文，如 "12+30="
    return my_onnx_model.predict(image)

resolver = ExprCaptchaResolver(my_ocr)
```

## 自定义 Resolver

```python
from shmtu_cas import CaptchaAnswer

class LocalOnnxResolver:
    def __init__(self, model_path: str):
        import onnxruntime as ort
        self.session = ort.InferenceSession(model_path)

    async def resolve(self, image_data: bytes) -> CaptchaAnswer:
        import numpy as np
        arr = np.frombuffer(image_data, dtype=np.uint8)
        # ... 预处理 + 推理 ...
        text = self.session.run(None, { ... })[0][0]
        return CaptchaAnswer.answer(text)
```
