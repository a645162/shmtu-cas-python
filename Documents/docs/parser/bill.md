# 账单 HTML 解析

> 版本：1.0.0

```python
from shmtu_cas import EpayAuth, parse_bill_page, get_total_pages

async with EpayAuth() as epay:
    # 拉第一页
    html = await epay.get_bill(page_no=1, tab_no="1")

    # 解析
    result = parse_bill_page(html)
    print(f"共 {result.total_pages} 页, 本页 {len(result.bills)} 条")

    for bill in result.bills:
        print(bill)
```

`parse_bill_page` 同时返回 `bills` + `total_pages` + `page_no` + `tab_no`；如果你已经有 `<tr>` 元素，可直接用 `parse_bill_item(tr_element)` 解析单条。
