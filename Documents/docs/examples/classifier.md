# 账单分类 + 位置翻译

> 版本：1.0.0

```python
from shmtu_cas import BillClassifier, PositionTranslator

classifier = BillClassifier.from_json("""
{
  "deposit": {"name": ["中行云充值"]},
  "bath":    {"target": ["淋浴", "热水"]},
  "canteen": {"target": ["食堂", "餐厅"]}
}
""")

print(classifier.classify("中行云充值", "商户"))   # BillCategory.DEPOSIT

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
