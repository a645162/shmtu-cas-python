# PositionTranslator

> 版本：1.0.0

```python
from shmtu_cas import PositionTranslator

translator = PositionTranslator.from_json("""
{
  "field": "target",
  "keywords": {
    "海馨楼食堂": {"position": "海馨楼", "room": "海馨第1食堂"}
  }
}
""")

print(translator.translate("海馨楼食堂-1F"))
# PositionEntry(position='海馨楼', room='海馨第1食堂')
```

## 配置字段

- `field`: 要在 `BillItem` 的哪个字段上做翻译（通常 `"target_user"` 或 `"item_type"`）
- `keywords`: 原始字符串 → `PositionEntry` 的精确 / 模糊映射表
