# CaptchaResolver 协议

> 版本：1.0.0

```python
from typing import Protocol, runtime_checkable
from shmtu_cas import CaptchaAnswer

@runtime_checkable
class CaptchaResolver(Protocol):
    async def resolve(self, image_data: bytes) -> CaptchaAnswer: ...
```

`EpayAuth(captcha_resolver=...)` 接受任何实现此协议的对象。

## CaptchaAnswer

```python
@dataclass
class CaptchaAnswer:
    value: str
    kind: CaptchaAnswerKind   # ANSWER | EXPRESSION
```

`CaptchaAnswer.answer("42")` 创建直接答案；`CaptchaAnswer.expression("12+30=")` 创建算式（库内取右侧）。
