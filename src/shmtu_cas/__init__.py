"""上海海事大学 CAS 客户端库 (Python 移植版)."""

from .auth.common import (
    CasAuth,
    CookieManager,
    build_client,
    cas_login,
    cas_redirect,
    get_execution,
)
from .auth.epay import EpayAuth
from .auth.wechat import WechatAuth
from .captcha.answer import CaptchaAnswer, CaptchaAnswerKind
from .captcha.http_ocr import CaptchaOcrHttp
from .captcha.resolver import (
    CaptchaResolver,
    ExprCaptchaResolver,
    ManualCaptchaResolver,
    OcrCaptchaResolver,
    OcrHttpCaptchaResolver,
)
from .captcha.tcp_ocr import CaptchaOcr
from .captcha.utils import fetch_captcha, get_expr_result
from .classifier.classify import BillCategory, BillClassifier, CategoryRule
from .classifier.position import PositionEntry, PositionTranslator
from .datatype.bill import BillItem, BillType, sum_money
from .datatype.status import BillItemStatus
from .parser.bill import (
    BillParseResult,
    get_total_pages,
    parse_bill_item,
    parse_bill_list,
    parse_bill_page,
)
from .parser.export import CsvExporter
from .parser.hot_water import HotWaterInfo, parse_hot_water_list
from .parser.person_account import (
    PersonAccountInfo,
    parse_person_account,
    person_account_to_dict,
)
from .session.exceptions import ManualCaptchaRequiredException
from .session.models import (
    LoginChallenge,
    LoginProbe,
    LoginSubmitResult,
    SessionProbe,
)
from .sync.engine import (
    AccountContext,
    AccountSyncJob,
    AccountSyncResult,
    BillStore,
    IncrementalBillStore,
    ParallelSyncSummary,
    SyncOptions,
    SyncPageProgress,
    SyncProgress,
    SyncRangePreset,
    SyncResult,
    SyncStatus,
    SyncStatusKind,
    full_sync,
    incremental_sync,
    sync_account,
    sync_accounts_parallel,
)

__all__ = [
    # auth
    "CasAuth",
    "CookieManager",
    "build_client",
    "cas_login",
    "cas_redirect",
    "get_execution",
    "EpayAuth",
    "WechatAuth",
    # captcha
    "CaptchaAnswer",
    "CaptchaAnswerKind",
    "CaptchaOcr",
    "CaptchaOcrHttp",
    "CaptchaResolver",
    "ExprCaptchaResolver",
    "ManualCaptchaResolver",
    "OcrCaptchaResolver",
    "OcrHttpCaptchaResolver",
    "fetch_captcha",
    "get_expr_result",
    # classifier
    "BillCategory",
    "BillClassifier",
    "CategoryRule",
    "PositionEntry",
    "PositionTranslator",
    # datatype
    "BillItem",
    "BillItemStatus",
    "BillType",
    "sum_money",
    # parser
    "BillParseResult",
    "CsvExporter",
    "HotWaterInfo",
    "PersonAccountInfo",
    "get_total_pages",
    "parse_bill_item",
    "parse_bill_list",
    "parse_bill_page",
    "parse_hot_water_list",
    "parse_person_account",
    "person_account_to_dict",
    # session
    "LoginChallenge",
    "LoginProbe",
    "LoginSubmitResult",
    "ManualCaptchaRequiredException",
    "SessionProbe",
    # sync
    "AccountContext",
    "AccountSyncJob",
    "AccountSyncResult",
    "BillStore",
    "IncrementalBillStore",
    "ParallelSyncSummary",
    "SyncOptions",
    "SyncPageProgress",
    "SyncProgress",
    "SyncRangePreset",
    "SyncResult",
    "SyncStatus",
    "SyncStatusKind",
    "full_sync",
    "incremental_sync",
    "sync_account",
    "sync_accounts_parallel",
]

__version__ = "0.1.0"
