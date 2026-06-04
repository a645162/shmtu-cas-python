"""CAS 通用底层 — 对齐 Rust ``cas/mod.rs`` 与 Kotlin ``auth/common/CasAuth``."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

import httpx
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

EPAY_BILL_URL = "https://ecard.shmtu.edu.cn/epay/consume/query"
HOT_WATER_URL = "http://hqzx.shmtu.edu.cn/cellphone/getHotWater"


def build_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """构造不自动重定向、保持 cookie store 的 ``httpx.AsyncClient``.

    对齐 Rust ``cas::create_client``.
    """
    return httpx.AsyncClient(
        follow_redirects=False,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )


async def get_execution(client: httpx.AsyncClient, url: str) -> str:
    """从 CAS 登录页获取 ``execution`` token. 对齐 Rust ``cas::get_execution``."""
    response = await client.get(url)
    if response.status_code != 200:
        msg = f"获取登录页面失败，状态码: {response.status_code}"
        raise RuntimeError(msg)
    document = BeautifulSoup(response.text, "lxml")
    element = document.select_one("input[name='execution']")
    if element is None:
        msg = "未找到execution元素"
        raise RuntimeError(msg)
    return str(element.get("value", ""))


@dataclass
class CasLoginResult:
    """``cas_login`` 的结构化结果 — 对齐 Rust ``CasAuthResult``."""

    variant: str  # "success" | "validate_code_error" | "password_error" | "failure"
    location: str = ""
    message: str = ""

    @property
    def is_success(self) -> bool:
        return self.variant == "success"

    @property
    def is_validate_code_error(self) -> bool:
        return self.variant == "validate_code_error"

    @property
    def is_password_error(self) -> bool:
        return self.variant == "password_error"

    @property
    def is_failure(self) -> bool:
        return self.variant == "failure"


async def cas_login(
    client: httpx.AsyncClient,
    url: str,
    *,
    username: str,
    password: str,
    validate_code: str,
    execution: str,
) -> CasLoginResult:
    """提交登录表单. 对齐 Rust ``cas::cas_login`` 与 Kotlin ``CasAuth.casLogin``."""
    response = await client.post(
        url,
        data={
            "username": username.strip(),
            "password": password.strip(),
            "validateCode": validate_code.strip(),
            "execution": execution.strip(),
            "_eventId": "submit",
            "geolocation": "",
        },
    )
    if response.status_code in (301, 302, 308):
        return CasLoginResult(variant="success", location=response.headers.get("location", ""))

    document = BeautifulSoup(response.text, "lxml")
    error_panel = document.select_one("#loginErrorsPanel")
    error_text = error_panel.get_text() if error_panel else ""

    if "account is not recognized" in error_text or "用户名或密码" in error_text:
        return CasLoginResult(variant="password_error")
    if "reCAPTCHA" in error_text or "验证码" in error_text:
        return CasLoginResult(variant="validate_code_error")
    return CasLoginResult(variant="failure", message=error_text)


async def cas_redirect(client: httpx.AsyncClient, url: str, max_hops: int = 10) -> str:
    """跟随重定向, 最多 ``max_hops`` 次. 对齐 Rust ``cas::cas_redirect``."""
    current = url
    for _ in range(max_hops):
        response = await client.get(current)
        if response.status_code in (301, 302, 308):
            location = response.headers.get("location")
            if not location:
                break
            current = location
            continue
        return current
    return current


def _merge_cookie_header(existing: str, set_cookie_headers: Iterable[str]) -> str:
    """合并 Set-Cookie 列表到已存在 cookie 串 — 对齐 Kotlin ``CasAuth.mergeCookies``."""
    cookies: dict[str, str] = {}
    if existing:
        for pair in existing.split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, _, v = pair.partition("=")
                cookies[k.strip()] = v.strip()
    for header in set_cookie_headers:
        first = header.split(";", 1)[0].strip()
        if "=" in first:
            k, _, v = first.partition("=")
            cookies[k.strip()] = v.strip()
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


# === Cookie Manager — 对齐 Rust ``cas/epay.rs::CookieJar`` 与 Kotlin ``CookieManager`` ===


class CookieManager:
    """管理 Cookie 字符串, 支持 JSON 序列化/反序列化.

    持久化 JSON 格式: ``{"key1": {"value": "v1"}, ...}`` (兼容 Rust).
    """

    def __init__(self) -> None:
        self._cookies: dict[str, str] = {}

    def restore(self, json_str: str) -> None:
        """从 JSON 字符串恢复 cookies; 同时接受原始 ``"k=v; k=v"`` 字符串作为兜底."""
        if not json_str.strip():
            return
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and "value" in value:
                        self._cookies[key] = str(value["value"])
                    else:
                        self._cookies[key] = str(value)
                return
        except (json.JSONDecodeError, ValueError):
            pass
        for pair in json_str.split(";"):
            pair = pair.strip()
            if "=" in pair:
                k, _, v = pair.partition("=")
                self._cookies[k.strip()] = v.strip()

    def extract(self) -> str:
        """导出 cookies 为 JSON 字符串 — 对齐 Rust ``CookieJar::extract``."""
        payload = {k: {"value": v} for k, v in self._cookies.items()}
        return json.dumps(payload, ensure_ascii=False)

    def add_from_set_cookie(self, header_val: str) -> None:
        """从 ``Set-Cookie`` 头解析 (e.g. ``"JSESSIONID=xxx; Path=/"``) 并加入."""
        first_segment = header_val.split(";", 1)[0].strip()
        if "=" not in first_segment:
            return
        name, _, value = first_segment.partition("=")
        name = name.strip()
        value = value.strip()
        if not name or not value:
            return
        self._cookies[name] = value

    def add_all(self, headers: Iterable[str]) -> None:
        for h in headers:
            self.add_from_set_cookie(h)

    def replace_from_mapping(self, mapping: dict[str, str]) -> None:
        self._cookies = {
            key.strip(): value.strip()
            for key, value in mapping.items()
            if key.strip() and value.strip()
        }

    def to_dict(self) -> dict[str, str]:
        return dict(self._cookies)

    def get(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self._cookies.items())

    def is_empty(self) -> bool:
        return not self._cookies

    def clear(self) -> None:
        self._cookies.clear()


def sync_cookie_manager_from_client(
    client: httpx.AsyncClient, manager: CookieManager
) -> None:
    """把 ``httpx`` 内部 cookie jar 镜像到 ``CookieManager``.

    Python 版本需要同时兼容:
    - 运行时请求: 依赖 ``httpx.AsyncClient`` 自带的 cookie jar
    - 会话导入/导出: 依赖 ``CookieManager`` 的 JSON 格式

    这里统一以 client jar 为准，避免 execution / captcha / redirect
    各阶段落在不同 cookie 视图里。

    注意: ``httpx.Cookies.items()`` 在某些版本会触发内部 ``__getitem__('HttpOnly')``
    (这是 httpx 的属性访问怪癖, 不是普通 dict 行为), 因此我们直接读 ``cookies.jar``
    这个底层的 ``RequestsCookieJar`` 来安全获取 ``(name, value)`` 列表.
    """

    pairs: dict[str, str] = {}
    jar = client.cookies.jar
    for cookie in jar:
        # 过滤掉 httpx 内部 sentinel
        if not cookie.name or cookie.value is None:
            continue
        pairs[cookie.name] = cookie.value
    manager.replace_from_mapping(pairs)


def sync_client_from_cookie_manager(
    client: httpx.AsyncClient, manager: CookieManager
) -> None:
    """把 ``CookieManager`` 中恢复出的 cookies 注入 ``httpx`` client."""

    cookies = manager.to_dict()
    client.cookies.clear()
    if cookies:
        client.cookies.update(cookies)


# === CasAuth — 对齐 Kotlin ``CasAuth`` 静态方法集合的 Python 包装类 ===


class CasAuth:
    """CAS 通用方法集合. 对齐 Kotlin ``CasAuth`` 伴生对象.

    Usage::

        client = CasAuth.create_client()
        execution, _ = await CasAuth.get_execution_async(client, login_url)
    """

    @staticmethod
    def create_client(timeout: float = 30.0) -> httpx.AsyncClient:
        return build_client(timeout)

    @staticmethod
    async def get_execution_async(
        client: httpx.AsyncClient, url: str, cookie: str = ""
    ) -> tuple[str, str]:
        """获取 ``execution`` token 和 ``JSESSIONID`` cookie. 对齐 Kotlin ``CasAuth.getExecution``."""
        headers: dict[str, str] = {}
        if cookie:
            headers["Cookie"] = cookie
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            return ("", "")

        document = BeautifulSoup(response.text, "lxml")
        element = document.select_one("input[name=execution]")
        execution = element.get("value", "").strip() if element else ""

        jsessionid = ""
        for header in response.headers.get_list("set-cookie"):
            if "JSESSIONID" in header:
                jsessionid = header.split(";", 1)[0]
                break
        if not jsessionid:
            jsessionid = cookie
        return (execution, jsessionid)

    @staticmethod
    async def cas_login_async(
        client: httpx.AsyncClient,
        url: str,
        username: str,
        password: str,
        validate_code: str,
        execution: str,
        cookie: str = "",
    ) -> tuple[int, str, str]:
        """``cas_login`` 的三方组返回版本, 兼容 Kotlin API 风格.

        Returns: ``(status_code, location_or_html, new_cookie)``.
        """
        request_headers: dict[str, str] = {
            "Host": "cas.shmtu.edu.cn",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "keep-alive",
        }
        if cookie:
            request_headers["Cookie"] = cookie.strip()

        response = await client.post(
            url,
            headers=request_headers,
            data={
                "username": username.strip(),
                "password": password.strip(),
                "validateCode": validate_code.strip(),
                "execution": execution.strip(),
                "_eventId": "submit",
                "geolocation": "",
            },
        )
        if response.status_code == 302:
            location = response.headers.get("Location", "")
            new_cookie = _merge_cookie_header(cookie, response.headers.get_list("set-cookie"))
            return (302, location, new_cookie)

        document = BeautifulSoup(response.text, "lxml")
        panel = document.select_one("#loginErrorsPanel")
        error_text = panel.get_text() if panel else ""

        if "account is not recognized" in error_text:
            return (-2, response.text, "")
        if "reCAPTCHA" in error_text:
            return (-1, response.text, "")
        return (response.status_code, error_text, "")

    @staticmethod
    async def cas_redirect_async(
        client: httpx.AsyncClient, url: str, cookie: str = ""
    ) -> tuple[int, str, str]:
        """``cas_redirect`` 的三方组返回版本, 兼容 Kotlin API 风格."""
        headers: dict[str, str] = {}
        if cookie:
            headers["Cookie"] = cookie
        response = await client.get(url, headers=headers)
        if response.status_code == 302:
            location = response.headers.get("Location", "")
            new_cookie = _merge_cookie_header(cookie, response.headers.get_list("set-cookie"))
            return (302, location, new_cookie)
        return (response.status_code, "", "")
