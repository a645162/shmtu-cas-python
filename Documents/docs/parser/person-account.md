# 个人账户页 HTML 解析

> 版本：0.1.0

`shmtu_cas.parser.parse_person_account` 解析一卡通个人账户页
`/epay/personaccount/index` 的 HTML，提取资金&安全信息、基本信息、头部标题与 CSRF。

```python
from shmtu_cas import (
    EpayAuth, parse_person_account, person_account_to_dict,
)

async with EpayAuth() as epay:
    # 登录后获取页面
    html = await epay.get_person_account_html()

    info = parse_person_account(html)
    print(f"{info.real_name} ({info.real_name_auth_status})")
    print(f"现金: {info.cash_balance_raw} 元")
    print(f"学工号: {info.student_id}")

    # 或者导出为 dict / JSON
    import json
    print(json.dumps(person_account_to_dict(info), ensure_ascii=False, indent=2))
```

## 解析字段

| 字段 | 类型 | 来源 |
|------|------|------|
| `real_name` | `str` | `.panel-title` 中的 `姓名：xxx` |
| `real_name_auth_status` | `str` | `.panel-title` 中的 `实名认证:xxx` |
| `cash_balance` | `float` | `现金资金` 数值 |
| `cash_balance_raw` | `str` | `现金资金` 原始字符串（去 "元"） |
| `security_question_status` | `str` | `安全保护问题` |
| `register_date` | `str` | `注册时间` |
| `student_id` | `str` | `学工号` |
| `email` | `str` | `电子邮箱` |
| `nickname` | `str` | `昵称` |
| `gender` | `str` | `性别` |
| `class_name` | `str` | `班级` |
| `mobile` | `str` | `手机` |
| `fixed_line` | `str` | `固话` |
| `id_type` | `str` | `证件类型` |
| `id_number` | `str` | `证件号码` |
| `remark` | `str` | `备注` |
| `user_type` | `str` | `用户类型` |
| `csrf_token` | `str` | `meta name="_csrf"` |
| `csrf_header` | `str` | `meta name="_csrf_header"` (默认 `X-CSRF-TOKEN`) |

## 解析规则要点

- `panel-title` 使用正则 `姓名[:：](\S+)` / `实名认证[:：](\S+)` 精确提取
- `#otherinfo` 容器下含两张 `<table>`（资金信息 + 安全信息），所有 tbody **合并**到同一 dict
- 中英文冒号 `:` / `：` 自动归一化

## CLI

```bash
# 登录 + 拉取 + 解析
python -m shmtu_cas.cli.main person-account -u <学号> -p <密码>

# 解析本地 HTML 文件
python -m shmtu_cas.cli.main parse-person-account -i <personaccount.html>
```

## 跨语言对齐

该 Parser 与 Kotlin `PersonAccountParser`、Rust `shmtu_cas::parser::parse_person_account`
解析结果完全等价，便于跨语言使用。
