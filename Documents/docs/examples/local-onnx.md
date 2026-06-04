# 本地 ONNX 自定义 Resolver

> 版本：1.0.0

```python
import asyncio
from shmtu_cas import EpayAuth, CaptchaAnswer

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

async def main():
    resolver = LocalOnnxResolver("captcha.onnx")
    async with EpayAuth(captcha_resolver=resolver) as epay:
        result = await epay.submit_login_auto("20210000", "pwd", max_retries=3)
        print(result.variant)
```

只要实现 `async def resolve(self, image_data: bytes) -> CaptchaAnswer`，`EpayAuth` 就会在登录流程里自动调用。
