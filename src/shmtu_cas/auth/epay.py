"""一卡通充值平台 (Epay) 认证 — 对齐 Rust ``cas/epay.rs`` 与 Kotlin ``auth/EpayAuth``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from ..session.models import (
    LoginChallenge,
    LoginProbe,
    LoginSubmitResult,
)
from .common import (
    EPAY_BILL_URL,
    CasAuth,
    CookieManager,
    cas_login,
    cas_redirect,
    get_execution,
)

if TYPE_CHECKING:
    from ..captcha.resolver import CaptchaResolver
    from ..datatype.bill import BillType


class EpayAuth:
    """一卡通充值平台 (https://ecard.shmtu.edu.cn) 认证客户端.

    三阶段设计 + Cookie 持久化:
        1. ``probe_login()`` 探测当前是否已登录
        2. ``prepare_challenge()`` 准备登录挑战 (execution + 验证码图片)
        3. ``submit_login()`` 提交登录
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
        self._login_url: str | None = None

    # ========== 上下文管理 ==========
    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> EpayAuth:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    # ========== 会话持久化 ==========
    def restore_session(self, json_str: str) -> None:
        """从 JSON 恢复 cookies (Android 端可对接 EncryptedSharedPreferences)."""
        self._cookies.restore(json_str)

    def extract_session(self) -> str:
        """导出当前 cookies 为 JSON."""
        return self._cookies.extract()

    def get_cookie_string(self) -> str:
        return self._cookies.get()

    # ========== TGC 复用 ==========
    async def try_reuse_tgc(self) -> bool:
        """尝试复用 TGC. 对齐 Rust 版本的 ``try_reuse_tgc``."""
        if self._login_url is None:
            msg = "尚未探测登录状态，请先调用 probe_login"
            raise RuntimeError(msg)
        execution, _ = await CasAuth.get_execution_async(
            self._client, self._login_url, self._cookies.get()
        )
        return execution == ""

    # ========== 探测 ==========
    async def probe_login(self) -> LoginProbe:
        """探测登录状态.  200 = 已登录, 302 = 需要登录."""
        url = f"{EPAY_BILL_URL}?pageNo=1&tabNo=1"
        response = await self._request_with_cookies("GET", url)
        self._cookies.add_all(response.headers.get_list("set-cookie"))

        if response.status_code == 200:
            return LoginProbe.already_logged_in()
        if response.status_code in (301, 302, 308):
            location = response.headers.get("location", "")
            if not location:
                msg = "重定向URL为空"
                raise RuntimeError(msg)
            self._login_url = location
            return LoginProbe.need_login(location)
        msg = f"探测登录状态失败，状态码: {response.status_code}"
        raise RuntimeError(msg)

    # ========== Challenge ==========
    async def prepare_challenge(self) -> LoginChallenge:
        """获取 ``execution`` + 验证码图片. 对齐 Rust ``EpayAuth::prepare_challenge``."""
        if self._login_url is None:
            msg = "尚未探测登录状态，请先调用 probe_login"
            raise RuntimeError(msg)
        execution = await get_execution(self._client, self._login_url)
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
        """手动路径: 提交登录 (验证码由调用方提供)."""
        if self._login_url is None:
            msg = "尚未探测登录状态，请先调用 probe_login"
            raise RuntimeError(msg)
        result = await cas_login(
            self._client,
            self._login_url,
            username=username,
            password=password,
            validate_code=validate_code,
            execution=execution,
        )
        if result.is_success:
            await cas_redirect(self._client, result.location)
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
        """自动路径: 循环尝试, 验证码由 ``captcha_resolver`` 处理.

        对齐 Kotlin ``EpayAuth.submitLogin(username, password, maxRetries)``.
        """
        if self._resolver is None:
            msg = "未设置 CaptchaResolver"
            raise RuntimeError(msg)

        # 先尝试 TGC 复用
        try:
            tgc_valid = await self.try_reuse_tgc()
        except RuntimeError:
            tgc_valid = False
        if tgc_valid:
            try:
                if await self.test_login_status():
                    return LoginSubmitResult.success()
            except RuntimeError:
                pass

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
        """测试是否已登录."""
        url = f"{EPAY_BILL_URL}?pageNo=1&tabNo=1"
        response = await self._request_with_cookies("GET", url)
        self._cookies.add_all(response.headers.get_list("set-cookie"))
        if response.status_code == 200:
            return True
        if response.status_code in (301, 302, 308):
            location = response.headers.get("location", "")
            if location:
                self._login_url = location
            return False
        msg = f"测试登录状态失败，状态码: {response.status_code}"
        raise RuntimeError(msg)

    async def get_bill(self, page_no: int = 1, tab_no: str = "1") -> str:
        """获取账单页面 HTML."""
        url = f"{EPAY_BILL_URL}?pageNo={page_no}&tabNo={tab_no}"
        response = await self._request_with_cookies("GET", url)
        self._cookies.add_all(response.headers.get_list("set-cookie"))
        if response.status_code == 200:
            return response.text
        if response.status_code in (301, 302, 308):
            msg = "未登录，需要重新登录"
            raise RuntimeError(msg)
        msg = f"获取账单失败，状态码: {response.status_code}"
        raise RuntimeError(msg)

    async def get_bill_by_type(self, page_no: int, bill_type: "BillType") -> str:
        """通过 BillType 枚举获取账单. 对齐 Kotlin ``EpayAuth.getBill(billType)``."""
        return await self.get_bill(page_no=page_no, tab_no=bill_type.tab_no)

    async def get_all_bills(
        self,
        bill_type: "BillType | None" = None,
        *,
        start_page: int = 1,
        max_pages: int = 50,
    ) -> list[str]:
        """翻页获取全部账单 HTML. 对齐 Kotlin ``EpayAuth.getAllBills``."""
        from ..datatype.bill import BillType

        bt = bill_type or BillType.ALL
        pages: list[str] = []
        for page in range(start_page, start_page + max_pages):
            try:
                html = await self.get_bill(page_no=page, tab_no=bt.tab_no)
            except RuntimeError:
                if not pages:
                    raise
                break
            if not html or "aazone" not in html:
                break
            pages.append(html)
        return pages

    # ========== 内部辅助 ==========
    async def _request_with_cookies(self, method: str, url: str) -> httpx.Response:
        headers: dict[str, str] = {}
        if not self._cookies.is_empty():
            headers["Cookie"] = self._cookies.get()
        return await self._client.request(method, url, headers=headers)

    async def _fetch_captcha(self) -> bytes:
        """拉取验证码图片, 合并 Set-Cookie 到本地 jar."""
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
