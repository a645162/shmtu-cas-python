# 手动验证码 + 拉账单 + 导出

> 版本：1.0.0

```python
import asyncio
from shmtu_cas import EpayAuth, LoginChallenge, parse_bill_page, CsvExporter

async def main():
    async with EpayAuth() as epay:
        probe = await epay.probe_login()
        if probe.is_already_logged_in:
            html = await epay.get_bill(page_no=1, tab_no="1")
        else:
            challenge: LoginChallenge = await epay.prepare_challenge()
            validate_code = input(f"请输入验证码 (execution={challenge.execution[:8]}...): ")
            result = await epay.submit_login(
                username="20210000",
                password="your_password",
                validate_code=validate_code,
                execution=challenge.execution,
            )
            if not result.is_success:
                print("登录失败:", result.variant, result.message)
                return
            html = await epay.get_bill(page_no=1, tab_no="1")

        page = parse_bill_page(html)
        print(f"共 {page.total_pages} 页, 本页 {len(page.bills)} 条")

        exporter = CsvExporter()
        exporter.export("bills.csv", page.bills)

asyncio.run(main())
```
