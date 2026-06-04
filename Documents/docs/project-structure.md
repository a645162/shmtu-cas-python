# 项目结构

> 版本：1.0.0

```
shmtu-cas-python/
├── pyproject.toml
├── README.md
├── Documents/
│   ├── REFERENCE.md                 # 已废弃，旧版参考
│   ├── package.json                 # vitepress 依赖与脚本
│   └── docs/                        # VitePress 站点
└── src/
    └── shmtu_cas/
        ├── __init__.py              # 公共 API re-export
        ├── datatype/                # BillItem / BillType / BillItemStatus
        ├── auth/                    # EpayAuth / WechatAuth / CasAuth / CookieManager
        ├── session/                 # 登录状态 dataclass + ManualCaptchaRequiredException
        ├── captcha/                 # 4 种 Resolver + TCP/HTTP OCR 客户端
        ├── parser/                  # HTML 解析 (账单/热水) + CSV 导出
        ├── classifier/              # BillClassifier + PositionTranslator
        ├── sync/                    # 同步状态机 + 增量/全量/并行
        └── cli/                     # 命令行入口
```

## License

MIT
