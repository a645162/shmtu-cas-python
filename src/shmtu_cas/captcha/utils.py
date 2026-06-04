"""验证码相关工具 (与 Rust ``captcha/mod.rs`` 对齐)."""

from __future__ import annotations

import httpx

CAPTCHA_URL = "https://cas.shmtu.edu.cn/cas/captcha"


async def fetch_captcha(client: httpx.AsyncClient) -> bytes:
    """拉取验证码图片字节 — 对齐 Rust ``captcha::fetch_captcha``.

    Args:
        client: 不自动跟随重定向的 ``httpx.AsyncClient`` 实例.

    Returns:
        PNG/JPEG 字节数据.

    Raises:
        RuntimeError: 状态码非 200.
        httpx.HTTPError: 网络层错误.
    """
    response = await client.get(CAPTCHA_URL)
    if response.status_code != 200:
        msg = f"获取验证码失败，状态码: {response.status_code}"
        raise RuntimeError(msg)
    return response.content


def get_expr_result(expr: str) -> str:
    """把 ``12+34=46`` 这样的算式取右侧答案 ``46``; 找不到 ``=`` 则按原样 trim 返回.

    对齐 Rust ``captcha::get_expr_result``.
    """
    idx = expr.rfind("=")
    if idx == -1:
        return expr.strip()
    return expr[idx + 1 :].strip()
