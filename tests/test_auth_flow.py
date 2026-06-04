from __future__ import annotations

import httpx
import pytest

from shmtu_cas.auth.epay import EpayAuth


@pytest.mark.asyncio
async def test_epay_login_keeps_cookie_chain_across_redirects() -> None:
    transport_state = {
        "service_callback_seen": False,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)

        if request.method == "POST" and url == "https://cas.shmtu.edu.cn/cas/login?service=ecard":
            cookie = request.headers.get("cookie", "")
            assert "CAS=cas-1" in cookie
            assert "CAPTCHA=cap-1" in cookie
            return httpx.Response(
                302,
                headers={
                    "Location": "https://ecard.shmtu.edu.cn/auth/callback?ticket=st-1",
                    "Set-Cookie": "CASTGC=castgc-1; Path=/; HttpOnly",
                },
            )

        if url == "https://ecard.shmtu.edu.cn/epay/consume/query?pageNo=1&tabNo=1":
            if request.headers.get("cookie") == "SERVICE=ok":
                return httpx.Response(200, text="ok")
            return httpx.Response(
                302,
                headers={
                    "Location": "https://cas.shmtu.edu.cn/cas/login?service=ecard",
                    "Set-Cookie": "TGC=tgc-1; Path=/; HttpOnly",
                },
            )

        if url == "https://cas.shmtu.edu.cn/cas/login?service=ecard":
            cookie = request.headers.get("cookie", "")
            if "CAS=cas-1" in cookie:
                return httpx.Response(
                    302,
                    headers={
                        "Location": "https://ecard.shmtu.edu.cn/auth/callback?ticket=st-1",
                    },
                )
            return httpx.Response(
                200,
                text="<html><input name='execution' value='e1'/></html>",
                headers={"Set-Cookie": "CAS=cas-1; Path=/; HttpOnly"},
            )

        if url == "https://cas.shmtu.edu.cn/cas/captcha":
            cookie = request.headers.get("cookie", "")
            assert "CAS=cas-1" in cookie
            return httpx.Response(
                200,
                content=b"fake-png",
                headers={"Set-Cookie": "CAPTCHA=cap-1; Path=/; HttpOnly"},
            )

        if url == "https://ecard.shmtu.edu.cn/auth/callback?ticket=st-1":
            transport_state["service_callback_seen"] = True
            return httpx.Response(
                302,
                headers={
                    "Location": "https://ecard.shmtu.edu.cn/epay/home",
                    "Set-Cookie": "SERVICE=ok; Path=/; HttpOnly",
                },
            )

        if url == "https://ecard.shmtu.edu.cn/epay/home":
            cookie = request.headers.get("cookie", "")
            assert "SERVICE=ok" in cookie
            return httpx.Response(200, text="home")

        raise AssertionError(f"unexpected request: {request.method} {url}")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        follow_redirects=False,
    ) as client:
        auth = EpayAuth(client=client)

        probe = await auth.probe_login()
        assert probe.is_need_login

        challenge = await auth.prepare_challenge()
        assert challenge.execution == "e1"
        assert challenge.captcha_image == b"fake-png"

        result = await auth.submit_login("user", "pass", "16", challenge.execution)
        assert result.is_success
        assert transport_state["service_callback_seen"] is True
        assert await auth.test_login_status() is True
