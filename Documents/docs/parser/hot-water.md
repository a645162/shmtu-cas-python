# 热水 HTML 解析

> 版本：1.0.0

```python
from shmtu_cas import parse_hot_water_list

html = open("hot_water.html").read()
records = parse_hot_water_list(html)
for r in records:
    print(f"{r.date} {r.time} {r.place} -{r.amount} 余 {r.balance}")
```

返回 `list[HotWaterInfo]`，每个包含 `date` / `time` / `place` / `amount` / `balance`。
