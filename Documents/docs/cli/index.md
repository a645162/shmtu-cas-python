# shmtu_cas.cli — 命令行

> 版本：1.0.0

## 入口

`pyproject.toml` 暴露的 `[project.scripts]` 入口 `shmtu_cas.cli:main`，因此安装后：

```bash
shmtu-cas --help
shmtu-cas version
shmtu-cas captcha --url http://127.0.0.1:21600/api/ocr --image captcha.png
```

等价于：

```bash
python -m shmtu_cas.cli ...
```
