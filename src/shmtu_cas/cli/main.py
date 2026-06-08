"""CLI 入口 — 7 个子命令: bill / hot-water / person-account / captcha-test / parse / parse-person-account / sync.

对齐 Rust ``shmtu-cas-cli`` (clap 子命令) 与 Kotlin ``cas_cli`` (手写解析).

使用标准库 ``argparse`` + 环境变量, 零新增依赖.

环境变量:
    SHMTU_USER_ID       学号 (优先于 SHMTU_USERNAME)
    SHMTU_USERNAME      用户名 (兼容旧 CLI)
    SHMTU_PASSWORD      密码
    SHMTU_OCR_HOST      TCP OCR 服务器地址 (默认 127.0.0.1)
    SHMTU_OCR_PORT      TCP OCR 服务器端口 (默认 21601)
    SHMTU_OCR_HTTP_URL  HTTP/RESTful OCR 服务器 URL (默认 http://127.0.0.1:5000)
"""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

from ..auth.epay import EpayAuth
from ..auth.wechat import WechatAuth
from ..captcha.answer import CaptchaAnswer, CaptchaAnswerKind
from ..captcha.http_ocr import CaptchaOcrHttp
from ..captcha.resolver import (
    CaptchaResolver,
    ManualCaptchaResolver,
    OcrCaptchaResolver,
    OcrHttpCaptchaResolver,
)
from ..captcha.tcp_ocr import CaptchaOcr
from ..captcha.utils import fetch_captcha, get_expr_result
from ..datatype.bill import BillItem, BillType
from ..parser.bill import parse_bill_list, parse_bill_page
from ..parser.export import CsvExporter
from ..parser.hot_water import parse_hot_water_list
from ..parser.person_account import (
    PersonAccountInfo,
    parse_person_account,
    person_account_to_dict,
)
from ..sync.engine import (
    SyncOptions,
    incremental_sync,
)
from .store import JsonBillStore


# =================== 通用选项 ===================


@dataclass(frozen=True)
class CommonOpts:
    """所有需要登录的子命令共享的选项."""

    username: str
    password: str
    captcha_mode: str  # "ocr" | "manual"
    ocr_host: str
    ocr_port: int
    ocr_server_type: str  # "tcp" | "http"
    ocr_http_url: str


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value else default


def _resolve_ocr_http_url(explicit: str | None) -> str:
    """解析最终的 HTTP OCR base URL.

    优先级:
      1. 命令行显式 --ocr-http-url
      2. 环境变量 ``SHMTU_OCR_HTTP_URL``
      3. 环境变量 ``SHMTU_OCR_HOST`` (拼接端口, HTTP 端口优先 21600)
      4. 硬编码默认 ``http://127.0.0.1:5000``

    端口优先级: ``SHMTU_HTTP_PORT`` > ``SHMTU_OCR_PORT`` (TCP) > 21600
    """
    if explicit:
        return explicit
    env_url = os.environ.get("SHMTU_OCR_HTTP_URL")
    if env_url:
        return env_url
    host = os.environ.get("SHMTU_OCR_HOST")
    if host:
        http_port = os.environ.get("SHMTU_HTTP_PORT")
        if not http_port:
            http_port = os.environ.get("SHMTU_OCR_PORT", "21600")
        return f"http://{host}:{http_port}"
    return "http://127.0.0.1:5000"


def _parse_common_args(args: argparse.Namespace) -> CommonOpts:
    """从 argparse Namespace + 环境变量构造 ``CommonOpts``.

    命令行参数优先于环境变量.
    """
    username = (
        args.username
        or _env("SHMTU_USER_ID", "")
        or _env("SHMTU_USERNAME", "")
    )
    password = args.password or _env("SHMTU_PASSWORD", "")
    # 只有当命令行没显式传入时, 才走 _resolve_ocr_http_url 自动拼接
    ocr_http_url = _resolve_ocr_http_url(args.ocr_http_url)
    return CommonOpts(
        username=username,
        password=password,
        captcha_mode=args.captcha,
        ocr_host=args.ocr_host,
        ocr_port=args.ocr_port,
        ocr_server_type=args.ocr_server_type,
        ocr_http_url=ocr_http_url,
    )


def _build_resolver(opts: CommonOpts) -> CaptchaResolver:
    """根据 ``captcha_mode`` + ``ocr_server_type`` 构造 resolver."""
    if opts.captcha_mode == "manual":
        return ManualCaptchaResolver(lambda image: _manual_captcha_prompt(image))

    if opts.ocr_server_type == "http":
        return OcrHttpCaptchaResolver.from_base_url(opts.ocr_http_url)
    return OcrCaptchaResolver.from_host_port(opts.ocr_host, opts.ocr_port)


def _manual_captcha_prompt(image: bytes) -> CaptchaAnswer:
    """把验证码图片写入本地, 阻塞读 stdin, 返回答案."""
    path = Path("captcha.png")
    path.write_bytes(image)
    print(f"验证码已保存到 {path}, 请查看后输入答案")
    try:
        answer = input("请输入验证码答案: ")
    except EOFError:
        answer = ""
    return CaptchaAnswer(value=answer.strip(), kind=CaptchaAnswerKind.ANSWER)


def _print_bill(bill: BillItem) -> None:
    """单行格式化输出账单 — 与 Rust/Kotlin CLI 风格保持一致."""
    print(
        f"{bill.date_time_formatted} | {bill.item_type} | "
        f"{bill.target_user} | {bill.money_str} | {bill.status_str}"
    )


def _print_person_account(info: PersonAccountInfo) -> None:
    """格式化输出个人账户信息 — 与 Rust/Kotlin CLI 风格保持一致."""
    print("===== 个人账户信息 =====")
    print(f"姓名: {info.real_name}    实名认证: {info.real_name_auth_status}")
    print()
    print("[资金信息]")
    print(f"现金资金: {info.cash_balance_raw} 元 ({info.cash_balance})")
    print()
    print("[安全信息]")
    print(f"安全保护问题: {info.security_question_status}")
    print(f"注册时间: {info.register_date}")
    print()
    print("[基本信息]")
    print(f"学工号: {info.student_id}")
    print(f"电子邮箱: {info.email}")
    print(f"真实姓名: {info.real_name}")
    print(f"昵称: {info.nickname}")
    print(f"性别: {info.gender}")
    if info.gender_from_id and info.gender_from_id != info.gender:
        print(f"身份证推断性别: {info.gender_from_id}")
    print(f"班级: {info.class_name}")
    print(f"手机号: {info.phone_num}")
    print(f"证件类型: {info.id_type}")
    print(f"证件号码: {info.id_number}")
    print(f"备注: {info.remark}")
    print(f"用户类型: {info.user_type}")
    if info.csrf_token:
        print()
        print("[CSRF]")
        print(f"token: {info.csrf_token}")
        print(f"header: {info.csrf_header}")


# =================== 登录流程 ===================


async def _login_epay(
    epay: EpayAuth,
    username: str,
    password: str,
    resolver: CaptchaResolver,
    *,
    max_retries: int = 5,
) -> bool:
    """探测 + 登录循环. 成功返回 True, 失败返回 False.

    流程对齐 Rust ``do_login`` 与 Kotlin ``submitLogin(auto)``.
    """
    print("正在探测登录状态...")
    probe = await epay.probe_login()
    if probe.is_already_logged_in:
        print("已经登录")
        return True

    for attempt in range(1, max_retries + 1):
        print(f"第 {attempt}/{max_retries} 次登录尝试")
        try:
            challenge = await epay.prepare_challenge()
        except RuntimeError as e:
            probe = await epay.probe_login()
            if probe.is_already_logged_in:
                print("检测到会话已建立")
                return True
            print(f"获取验证码失败: {e}")
            continue
        print(f"验证码大小: {len(challenge.captcha_image)} bytes")

        try:
            answer = await resolver.resolve(challenge.captcha_image)
        except Exception as e:  # noqa: BLE001
            print(f"验证码解析失败: {e}")
            continue
        validate_code = answer.into_final_answer()
        print(f"验证码答案: {validate_code}")

        try:
            result = await epay.submit_login(
                username=username,
                password=password,
                validate_code=validate_code,
                execution=challenge.execution,
            )
        except RuntimeError as e:
            print(f"提交登录失败: {e}")
            continue

        if result.is_success:
            if await epay.test_login_status():
                print("登录验证成功！")
                return True
            probe = await epay.probe_login()
            if probe.is_already_logged_in:
                print("登录验证成功！")
                return True
            print("登录验证失败, 重试...")
            continue
        if result.is_password_error:
            print("用户名或密码错误")
            return False
        if result.is_validate_code_error:
            print("验证码错误, 重试中...")
            continue
        print(f"登录失败: {result.variant}: {result.message}")
        return False
    return False


async def _login_wechat(
    wx: WechatAuth,
    username: str,
    password: str,
    resolver: CaptchaResolver,
    *,
    max_retries: int = 5,
) -> bool:
    """Wechat 平台登录流程. 对齐 Rust ``HotWater`` 分支."""
    print("正在探测登录状态...")
    probe = await wx.probe_login()
    if probe.is_already_logged_in:
        print("已经登录")
        return True

    for attempt in range(1, max_retries + 1):
        print(f"第 {attempt}/{max_retries} 次登录尝试")
        try:
            challenge = await wx.prepare_challenge()
        except RuntimeError as e:
            probe = await wx.probe_login()
            if probe.is_already_logged_in:
                print("检测到会话已建立")
                return True
            print(f"获取验证码失败: {e}")
            continue
        print(f"验证码大小: {len(challenge.captcha_image)} bytes")

        try:
            answer = await resolver.resolve(challenge.captcha_image)
        except Exception as e:  # noqa: BLE001
            print(f"验证码解析失败: {e}")
            continue
        validate_code = answer.into_final_answer()
        print(f"验证码答案: {validate_code}")

        try:
            result = await wx.submit_login(
                username=username,
                password=password,
                validate_code=validate_code,
                execution=challenge.execution,
            )
        except RuntimeError as e:
            print(f"提交登录失败: {e}")
            continue

        if result.is_success:
            if await wx.test_login_status():
                print("登录验证成功！")
                return True
            probe = await wx.probe_login()
            if probe.is_already_logged_in:
                print("登录验证成功！")
                return True
            print("登录验证失败, 重试...")
            continue
        if result.is_password_error:
            print("用户名或密码错误")
            return False
        if result.is_validate_code_error:
            print("验证码错误, 重试中...")
            continue
        print(f"登录失败: {result.variant}: {result.message}")
        return False
    return False


# =================== 子命令实现 ===================


async def _cmd_bill(args: argparse.Namespace) -> int:
    """``shmtu-cas bill`` 子命令: 登录 + 拉账单 + 可选 CSV 导出."""
    opts = _parse_common_args(args)
    if not opts.username or not opts.password:
        print("Error: --username 与 --password 必填 (或设置 SHMTU_USER_ID / SHMTU_PASSWORD)")
        return 1
    bill_type = BillType.parse(args.tab)

    resolver = _build_resolver(opts)
    async with EpayAuth(captcha_resolver=resolver) as epay:
        if not await _login_epay(epay, opts.username, opts.password, resolver):
            return 1

        print("正在获取账单...")
        all_bills: list[BillItem] = []
        current_page = args.page
        while True:
            try:
                html = await epay.get_bill(
                    page_no=current_page, tab_no=bill_type.tab_no
                )
            except RuntimeError as e:
                print(f"获取第 {current_page} 页失败: {e}")
                return 1
            page_result = parse_bill_page(html)
            if not page_result.bills and current_page == args.page:
                print("没有找到账单记录")
                return 0
            print(
                f"第 {current_page}/{page_result.total_pages} 页: "
                f"找到 {len(page_result.bills)} 条记录"
            )
            total_pages = page_result.total_pages
            all_bills.extend(page_result.bills)
            if not args.all_pages or current_page >= total_pages:
                break
            current_page += 1

        print(f"共 {len(all_bills)} 条账单记录")
        for bill in all_bills:
            _print_bill(bill)

        if args.output:
            CsvExporter().export(args.output, all_bills)
            print(f"已导出到 {args.output}")
    return 0


async def _cmd_hot_water(args: argparse.Namespace) -> int:
    """``shmtu-cas hot-water`` 子命令: 登录 + 拉热水信息."""
    opts = _parse_common_args(args)
    if not opts.username or not opts.password:
        print("Error: --username 与 --password 必填")
        return 1

    resolver = _build_resolver(opts)
    async with WechatAuth(captcha_resolver=resolver) as wx:
        if not await _login_wechat(wx, opts.username, opts.password, resolver):
            return 1

        print("正在获取热水信息...")
        try:
            html = await wx.get_hot_water()
        except RuntimeError as e:
            print(f"获取热水信息失败: {e}")
            return 1
        info_list = parse_hot_water_list(html)
        if not info_list:
            if "Fatal error" in html or "404 Not Found" in html or "Exception" in html:
                print("[服务器错误] SHMTU 热水接口返回错误页:")
                print(html[:500])
            else:
                print("没有找到热水信息 (可能 HTML 结构变化或宿舍楼信息为空)")
            return 0

        print(f"共 {len(info_list)} 栋楼")
        for info in info_list:
            print(
                f"{info.building}号楼: 温度 {info.temperature:.1f}℃, "
                f"水位 {info.water_level:.0f}%"
            )
    return 0


async def _cmd_captcha_test(args: argparse.Namespace) -> int:
    """``shmtu-cas captcha-test`` 子命令: 拉取一张验证码并测试 OCR 服务."""
    from ..auth.common import CasAuth

    print("正在获取验证码...")
    async with CasAuth.create_client() as client:
        try:
            image = await fetch_captcha(client)
        except Exception as e:  # noqa: BLE001
            print(f"获取验证码失败: {e}")
            return 1
    print(f"验证码大小: {len(image)} bytes")
    Path("captcha_test.png").write_bytes(image)
    print("已保存验证码图片到 captcha_test.png")

    print("正在识别验证码...")
    # 解析最终的 HTTP URL (若命令行/SHMTU_OCR_HTTP_URL 都没设, 从 SHMTU_OCR_HOST 拼)
    ocr_http_url = _resolve_ocr_http_url(args.ocr_http_url)
    if args.ocr_server_type == "http":
        ocr = CaptchaOcrHttp(base_url=ocr_http_url)
        try:
            expr = await ocr.ocr_auto_retry_async(image, max_retries=3)
        except Exception as e:  # noqa: BLE001
            print(f"HTTP OCR 识别失败: {e}")
            return 1
    else:
        ocr = CaptchaOcr(host=args.ocr_host, port=args.ocr_port)
        try:
            expr = ocr.ocr_auto_retry(image, max_retries=3)
        except Exception as e:  # noqa: BLE001
            print(f"TCP OCR 识别失败: {e}")
            return 1
    print(f"OCR 算式: {expr}")
    print(f"验证码答案: {get_expr_result(expr)}")
    return 0


def _cmd_parse(args: argparse.Namespace) -> int:
    """``shmtu-cas parse`` 子命令: 解析本地 HTML 账单文件."""
    try:
        html = Path(args.input).read_text(encoding="utf-8")
    except OSError as e:
        print(f"读取文件失败: {e}")
        return 1

    bills = parse_bill_list(html)
    if not bills:
        print("没有找到账单记录")
        return 0
    print(f"找到 {len(bills)} 条账单记录")
    for bill in bills:
        _print_bill(bill)

    if args.output:
        CsvExporter().export(args.output, bills)
        print(f"已导出到 {args.output}")
    return 0


async def _cmd_person_account(args: argparse.Namespace) -> int:
    """``shmtu-cas person-account`` 子命令: 登录 + 拉取个人账户页 + 解析."""
    opts = _parse_common_args(args)
    if not opts.username or not opts.password:
        print("Error: --username 与 --password 必填 (或设置 SHMTU_USER_ID / SHMTU_PASSWORD)")
        return 1

    resolver = _build_resolver(opts)
    async with EpayAuth(captcha_resolver=resolver) as epay:
        if not await _login_epay(epay, opts.username, opts.password, resolver):
            return 1

        print("正在获取个人账户信息...")
        try:
            html = await epay.get_person_account_html()
        except RuntimeError as e:
            print(f"获取个人账户页失败: {e}")
            return 1
        info = parse_person_account(html)
        _print_person_account(info)

        if args.output:
            import json
            Path(args.output).write_text(
                json.dumps(person_account_to_dict(info), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"已导出到 {args.output}")
    return 0


def _cmd_parse_person_account(args: argparse.Namespace) -> int:
    """``shmtu-cas parse-person-account`` 子命令: 解析本地个人账户 HTML 文件."""
    try:
        html = Path(args.input).read_text(encoding="utf-8")
    except OSError as e:
        print(f"读取文件失败: {e}")
        return 1

    info = parse_person_account(html)
    _print_person_account(info)

    if args.output:
        import json
        Path(args.output).write_text(
            json.dumps(person_account_to_dict(info), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"已导出到 {args.output}")
    return 0


async def _cmd_sync(args: argparse.Namespace) -> int:
    """``shmtu-cas sync`` 子命令: 增量同步到本地 JSON."""
    opts = _parse_common_args(args)
    if not opts.username or not opts.password:
        print("Error: --username 与 --password 必填")
        return 1

    resolver = _build_resolver(opts)
    async with EpayAuth(captcha_resolver=resolver) as epay:
        if not await _login_epay(epay, opts.username, opts.password, resolver):
            return 1

        print("正在增量同步账单...")
        store = JsonBillStore(args.store)
        prev_count = sum(1 for b in store.all_bills() if b.get("number"))
        print(f"本地已有 {prev_count} 条记录")

        sync_opts = SyncOptions(
            start_page=1,
            max_pages=args.max_pages,
            bill_type=BillType.ALL,
            early_stop_threshold=args.early_stop,
            since_timestamp=None,
        )

        result = await incremental_sync(epay, store, sync_opts)
        print(
            f"同步完成: 新增 {result.new_count} 条, 翻页 {result.pages_fetched}, "
            f"{'早停' if result.early_stopped else '正常结束'}"
        )
        for bill in result.new_bills:
            _print_bill(bill)

        if result.new_count > 0:
            store.save()
            print(f"已保存到 {args.store}")
    return 0


# =================== argparse ===================


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """挂载所有需要登录的子命令的共享参数."""
    parser.add_argument(
        "-u", "--username",
        help="用户名/学号 (env: SHMTU_USER_ID, fallback SHMTU_USERNAME)",
    )
    parser.add_argument(
        "-p", "--password",
        help="密码 (env: SHMTU_PASSWORD)",
    )
    parser.add_argument(
        "-c", "--captcha",
        choices=("ocr", "manual"),
        default="ocr",
        help="验证码模式: ocr (默认) / manual",
    )
    parser.add_argument(
        "--ocr-host",
        default=_env("SHMTU_OCR_HOST", "127.0.0.1"),
        help="TCP OCR 服务器地址 (env: SHMTU_OCR_HOST, 默认 127.0.0.1)",
    )
    parser.add_argument(
        "--ocr-port",
        type=int,
        default=int(_env("SHMTU_OCR_PORT", "21601")),
        help="TCP OCR 服务器端口 (env: SHMTU_OCR_PORT, 默认 21601)",
    )
    parser.add_argument(
        "--ocr-server-type",
        choices=("tcp", "http"),
        default="tcp",
        help="OCR 服务器协议 (默认 tcp)",
    )
    parser.add_argument(
        "--ocr-http-url",
        default=None,
        help="HTTP OCR 服务器 URL (env: SHMTU_OCR_HTTP_URL, fallback SHMTU_OCR_HOST, 默认 http://127.0.0.1:5000)",
    )


def build_parser() -> argparse.ArgumentParser:
    """构造顶级 argparse parser."""
    parser = argparse.ArgumentParser(
        prog="shmtu-cas",
        description="上海海事大学 CAS 登录与账单查询工具",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="shmtu-cas 0.1.0 (Python 移植版)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # bill
    p_bill = subparsers.add_parser("bill", help="登录 CAS 并获取账单")
    _add_common_args(p_bill)
    p_bill.add_argument("-o", "--output", help="CSV 输出路径")
    p_bill.add_argument(
        "--tab", default="all",
        choices=("all", "success", "not_paid", "failure"),
        help="账单类型 (默认 all)",
    )
    p_bill.add_argument("--page", type=int, default=1, help="起始页 (默认 1)")
    p_bill.add_argument(
        "--all-pages", action="store_true", help="翻完所有页 (否则只拉起始页)",
    )

    # hot-water
    p_hw = subparsers.add_parser("hot-water", help="登录微信平台并获取宿舍热水状态")
    _add_common_args(p_hw)

    # person-account
    p_pa = subparsers.add_parser(
        "person-account", help="登录一卡通平台并获取个人账户信息(余额/认证/学工号/证件等)"
    )
    _add_common_args(p_pa)
    p_pa.add_argument("-o", "--output", help="JSON 输出路径 (可选)")

    # captcha-test
    p_ct = subparsers.add_parser("captcha-test", help="测试验证码 OCR 服务")
    p_ct.add_argument(
        "--ocr-host",
        default=_env("SHMTU_OCR_HOST", "127.0.0.1"),
        help="TCP OCR 服务器地址 (env: SHMTU_OCR_HOST, 默认 127.0.0.1)",
    )
    p_ct.add_argument(
        "--ocr-port",
        type=int,
        default=int(_env("SHMTU_OCR_PORT", "21601")),
        help="TCP OCR 服务器端口 (env: SHMTU_OCR_PORT, 默认 21601)",
    )
    p_ct.add_argument(
        "--ocr-server-type",
        choices=("tcp", "http"),
        default="tcp",
        help="OCR 服务器协议 (默认 tcp)",
    )
    p_ct.add_argument(
        "--ocr-http-url",
        default=None,
        help="HTTP OCR 服务器 URL (env: SHMTU_OCR_HTTP_URL, fallback SHMTU_OCR_HOST, 默认 http://127.0.0.1:5000)",
    )

    # parse
    p_parse = subparsers.add_parser("parse", help="解析本地 HTML 账单文件")
    p_parse.add_argument("-i", "--input", required=True, help="HTML 文件路径")
    p_parse.add_argument("-o", "--output", help="CSV 输出路径")

    # parse-person-account
    p_ppa = subparsers.add_parser("parse-person-account", help="解析本地个人账户 HTML 文件")
    p_ppa.add_argument("-i", "--input", required=True, help="HTML 文件路径")
    p_ppa.add_argument("-o", "--output", help="JSON 输出路径 (可选)")

    # sync
    p_sync = subparsers.add_parser("sync", help="增量同步账单到本地 JSON 存档")
    _add_common_args(p_sync)
    p_sync.add_argument(
        "-s", "--store", default="bills.json", help="本地 JSON 存档路径 (默认 bills.json)",
    )
    p_sync.add_argument(
        "--tab", default="all",
        choices=("all", "success", "not_paid", "failure"),
        help="账单类型 (默认 all)",
    )
    p_sync.add_argument(
        "--early-stop", type=int, default=5,
        help="连续遇到多少条已知条目后早停 (默认 5)",
    )
    p_sync.add_argument(
        "--max-pages", type=int, default=100, help="最大翻页数 (默认 100)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口函数. 由 ``console_scripts`` 调用."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "parse":
        return _cmd_parse(args)
    if args.command == "parse-person-account":
        return _cmd_parse_person_account(args)
    if args.command == "bill":
        return asyncio.run(_cmd_bill(args))
    if args.command == "hot-water":
        return asyncio.run(_cmd_hot_water(args))
    if args.command == "person-account":
        return asyncio.run(_cmd_person_account(args))
    if args.command == "captcha-test":
        return asyncio.run(_cmd_captcha_test(args))
    if args.command == "sync":
        return asyncio.run(_cmd_sync(args))

    parser.print_help()
    return 1


__all__ = ["main", "build_parser", "CommonOpts"]
