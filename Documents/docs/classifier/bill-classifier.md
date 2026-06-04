# BillClassifier

> 版本：1.0.0

```python
from shmtu_cas import BillClassifier

classifier = BillClassifier.from_json("""
{
  "deposit": {"name": ["中行云充值"]},
  "bath":    {"target": ["淋浴", "热水"]},
  "canteen": {"target": ["食堂", "餐厅"]}
}
""")

print(classifier.classify("中行云充值", "商户"))   # BillCategory.DEPOSIT
print(classifier.classify("洗澡", "热水房"))        # BillCategory.BATH
print(classifier.classify("午餐", "海馨楼食堂-1F"))  # BillCategory.CANTEEN
```

## 规则

```python
from shmtu_cas import BillClassifier, BillCategory, CategoryRule

rules = [
    CategoryRule(
        category=BillCategory.DEPOSIT,
        name_keywords=["充值", "退款"],
        target_keywords=[],
        priority=10,
    ),
]
classifier = BillClassifier(rules)
```

匹配规则：先按 `priority` 降序，再判断 `name_keywords` / `target_keywords` 包含关系。
