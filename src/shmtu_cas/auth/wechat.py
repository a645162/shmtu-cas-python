"""微信认证 (热水平台) — 对齐 Rust ``cas/wechat.rs`` 与 Kotlin ``auth/WechatAuth``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from ..session.models import (
    LoginChallenge,
    LoginProbe,
    LoginSubmitResult,
)
from .common import (
    HOT_WATER_URL,
    CasAuth,
    CookieManager,
    cas_login,
    cas_redirect,
)

if TYPE_CHECKING:
    from ..captcha.resolver import CaptchaResolver


class WechatAuth:
    """热水平台 (http://hqzx.shmtu.edu.cn) 认证客户端.

    与 Epay 类似的三阶段设计, 多一跳 ``wengine_new_ticket`` 拿到真正的 CAS 登录 URL.
    """

    def __init__(
        self,
        captcha_resolver: "CaptchaResolver | None" = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._resolver: CaptchaResolver | None = captcha_resolver
        self._cookies = CookieManager()
        self._client = client or CasAuth.create_client()
        self._owns_client = client is None
        self._login_w_url: str | None = None
        self._login_url: str | None = None

    # ========== 上下文管理 ==========
    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> WechatAuth:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # ========== 会话持久化 ==========
    def restore_session(self, json_str: str) -> None:
        self._cookies.restore(json_str)

    def extract_session(self) -> str:
        return self._cookies.extract()

    def get_cookie_string(self) -> str:
        return self._cookies.get()

    # ========== 探测 ==========
    async def probe_login(self) -> LoginProbe:
        """探测热水登录状态.  200 = 已登录, 302 = 需要登录 (给 wengine_new_ticket)."""
        response = await self._request_with_cookies("GET", HOT_WATER_URL)
        self._cookies.add_all(response.headers.get_list("set-cookie"))

        if response.status_code == 200:
            return LoginProbe.already_logged_in()
        if response.status_code in (301, 302, 308):
            location = response.headers.get("location", "")
            if not location:
                msg = "重定向URL为空"
                raise RuntimeError(msg)
            self._login_w_url = location
            return LoginProbe.need_login(location)
        msg = f"探测热水登录状态失败，状态码: {response.status_code}"
        raise RuntimeError(msg)

    # ========== Challenge ==========
    async def prepare_challenge(self) -> LoginChallenge:
        """获取 ``execution`` + 验证码图片. 多一跳 wengine_new_ticket."""
        if self._login_w_url is None:
            msg = "尚未探测登录状态，请先调用 probe_login"
            raise RuntimeError(msg)
        cas_login_url, new_cookie = await self._fetch_wengine_ticket(self._login_w_url)
        if new_cookie:
            self._cookies.restore(new_cookie)

        execution, _ = await CasAuth.get_execution_async(
            self._client, cas_login_url, self._cookies.get()
        )
        if not execution:
            msg = "获取 execution 失败"
            raise RuntimeError(msg)
        self._login_url = cas_login_url
        image_data = await self._fetch_captcha()
        return LoginChallenge(execution=execution, captcha_image=image_data)

    # ========== 提交登录 ==========
    async def submit_login(
        self,
        username: str,
        password: str,
        validate_code: str,
        execution: str,
    ) -> LoginSubmitResult:
        """手动路径: 提交登录."""
        if self._login_w_url is None:
            msg = "尚未探测登录状态"
            raise RuntimeError(msg)

        # 重新拉一次 ticket 以保证 cookie 最新
        cas_login_url, new_cookie = await self._fetch_wengine_ticket(self._login_w_url)
        if new_cookie:
            self._cookies.restore(new_cookie)

        result = await cas_login(
            self._client,
            cas_login_url,
            username=username,
            password=password,
            validate_code=validate_code,
            execution=execution,
        )
        if result.is_success:
            final_url = f"{result.location}&from={HOT_WATER_URL}"
            await cas_redirect(self._client, final_url)
            return LoginSubmitResult.success()
        if result.is_password_error:
            return LoginSubmitResult.password_error()
        if result.is_validate_code_error:
            return LoginSubmitResult.validate_code_error()
        return LoginSubmitResult.failure(result.message)

    async def submit_login_auto(
        self,
        username: str,
        password: str,
        *,
        max_retries: int = 5,
    ) -> LoginSubmitResult:
        """自动路径: 循环尝试, 验证码由 ``captcha_resolver`` 处理."""
        if self._resolver is None:
            msg = "未设置 CaptchaResolver"
            raise RuntimeError(msg)

        last_result: LoginSubmitResult | None = None
        for _ in range(1, max_retries + 1):
            try:
                challenge = await self.prepare_challenge()
            except RuntimeError as e:
                last_result = LoginSubmitResult.failure(str(e))
                continue
            try:
                answer = await self._resolver.resolve(challenge.captcha_image)
            except Exception as e:  # noqa: BLE001
                last_result = LoginSubmitResult.failure(f"验证码解析失败: {e}")
                continue
            try:
                submit = await self.submit_login(
                    username, password, answer.into_final_answer(), challenge.execution
                )
            except RuntimeError as e:
                last_result = LoginSubmitResult.failure(str(e))
                continue
            if submit.is_success:
                return submit
            if submit.is_password_error:
                return submit
            last_result = submit
        return last_result or LoginSubmitResult.failure("登录重试次数耗尽")

    # ========== 业务方法 ==========
    async def test_login_status(self) -> bool:
        response = await self._request_with_cookies("GET", HOT_WATER_URL)
        self._cookies.add_all(response.headers.get_list("set-cookie"))
        if response.status_code == 200:
            return True
        if response.status_code in (301, 302, 308):
            location = response.headers.get("location", "")
            if location:
                self._login_w_url = location
            return False
        msg = f"测试热水登录状态失败，状态码: {response.status_code}"
        raise RuntimeError(msg)

    async def get_hot_water(self) -> str:
        """获取热水信息 HTML. 对齐 Rust ``WechatAuth::get_hot_water``."""
        response = await self._request_with_cookies("GET", HOT_WATER_URL)
        self._cookies.add_all(response.headers.get_list("set-cookie"))
        if response.status_code == 200:
            return response.text
        msg = f"获取热水信息失败，状态码: {response.status_code}"
        raise RuntimeError(msg)

    # ========== 内部辅助 ==========
    async def _request_with_cookies(self, method: str, url: str) -> httpx.Response:
        headers: dict[str, str] = {}
        if not self._cookies.is_empty():
            headers["Cookie"] = self._cookies.get()
        return await self._client.request(method, url, headers=headers)

    async def _fetch_wengine_ticket(self, url: str) -> tuple[str, str]:
        """跟随 wengine_new_ticket 一次跳转, 拿到 CAS 登录 URL.

        Returns: ``(cas_login_url, new_cookie_string)``.
        """
        response = await self._client.get(url)
        self._cookies.add_all(response.headers.get_list("set-cookie"))
        if response.status_code not in (301, 302, 308):
            msg = f"wengine_new_ticket未返回重定向，状态码: {response.status_code}"
            raise RuntimeError(msg)
        cas_login_url = response.headers.get("location", "")
        if not cas_login_url:
            msg = "CAS登录URL为空"
            raise RuntimeError(msg)
        return (cas_login_url, self._cookies.get())

    async def _fetch_captcha(self) -> bytes:
        headers: dict[str, str] = {}
        if not self._cookies.is_empty():
            headers["Cookie"] = self._cookies.get()
        response = await self._client.get(
            "https://cas.shmtu.edu.cn/cas/captcha", headers=headers
        )
        if response.status_code != 200:
            msg = f"获取验证码失败，状态码: {response.status_code}"
            raise RuntimeError(msg)
        self._cookies.add_all(response.headers.get_list("set-cookie"))
        return response.content
