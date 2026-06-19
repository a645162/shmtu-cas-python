"""OCR 模型下载 — 对齐 Rust ``ocr_model``、Kotlin ``ModelDownloader`` 与 C++ ``ModelDownloader``.

源:
    - Gitee (默认主源, 国内访问稳定)
    - GitHub (fallback, 全球可访问)

能力:
    - 下载并解析 ``model-assets.json`` manifest
    - 解析 manifest 定位 ``engine=ncnn`` + 指定 ``precision`` 的产物
    - 主源/fallback 自动切换下载模型文件
    - SHA256 校验
    - 列出可用 release tags (Gitee API 优先, GitHub fallback)
    - 解析最新可用 tag (Gitee API 优先)

仅使用标准库 (``urllib.request`` + ``hashlib``), 零新增依赖.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# =================== 常量 (与 Rust/Kotlin/C++ 端对齐) ===================

#: GitHub Releases API (fallback 列表源)
GITHUB_RELEASES_API = "https://api.github.com/repos/a645162/shmtu-cas-ocr-model/releases"
#: Gitee Releases API (默认主列表源, 国内访问更稳定)
GITEE_RELEASES_API = "https://gitee.com/api/v5/repos/a645162/shmtu-cas-ocr-model/releases"

#: GitHub release asset 下载前缀
GITHUB_BASE_URL = "https://github.com/a645162/shmtu-cas-ocr-model/releases/download"
#: Gitee release asset 下载前缀
GITEE_BASE_URL = "https://gitee.com/a645162/shmtu-cas-ocr-model/releases/download"

#: 默认 release tag — 对齐 Kotlin ``SHMTU_NCNN_Model.V2_DEFAULT_TAG``
DEFAULT_TAG = "v2.0.5"
#: 默认 backbone — 对齐 Kotlin ``SHMTU_NCNN_Model.V2_DEFAULT_BACKBONE``
DEFAULT_BACKBONE = "mobilenet_v3_small"
#: 默认精度 — 对齐 Kotlin ``SHMTU_NCNN_Model.V2_DEFAULT_PRECISION``
DEFAULT_PRECISION = "fp16"
#: manifest 文件名 — 对齐 Kotlin ``SHMTU_NCNN_Model.V2_MANIFEST_FILENAME``
MANIFEST_NAME = "model-assets.json"

#: 单次下载失败后的总尝试次数 (主源/备用源交替, 类似 Kotlin 端 ``MAX_DOWNLOAD_ATTEMPTS = 3``)
MAX_DOWNLOAD_ATTEMPTS = 3
#: HTTP 请求超时 (秒)
DEFAULT_TIMEOUT = 30.0
#: 默认 User-Agent
DEFAULT_USER_AGENT = "shmtu-cas-python/1.0"

#: 接受的 semver tag 模式, 其它一律忽略
SEMVER_TAG_REGEX = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

logger = logging.getLogger("shmtu_cas.model_download")


# =================== 枚举 & 数据类型 ===================


class ModelSource(Enum):
    """模型下载源 — 对齐 Kotlin ``SHMTU_NCNN_Model.ModelSource``."""

    GITEE = "gitee"
    GITHUB = "github"

    @property
    def other(self) -> ModelSource:
        """返回 ``self`` 的备选源 (GITEE <-> GITHUB 互相切换)."""
        if self is ModelSource.GITEE:
            return ModelSource.GITHUB
        return ModelSource.GITEE

    def releases_api(self) -> str:
        return GITEE_RELEASES_API if self is ModelSource.GITEE else GITHUB_RELEASES_API

    def base_url(self) -> str:
        return GITEE_BASE_URL if self is ModelSource.GITEE else GITHUB_BASE_URL

    def file_url(self, tag: str, file_name: str) -> str:
        """拼接 ``<base>/<tag>/<file_name>`` 形式的下载链接."""
        return f"{self.base_url()}/{tag}/{file_name}"


@dataclass(frozen=True)
class ModelAssetFile:
    """manifest 中单个文件条目 — 对齐 Kotlin ``OcrAssetFile``."""

    path: str
    release_asset_name: str
    sha256: str | None = None


@dataclass(frozen=True)
class ModelArtifact:
    """manifest 中 ``artifacts[engine][precision]`` 节点 — 对齐 Kotlin ``OcrArtifactInfo``."""

    engine: str
    precision: str
    format: str | None
    files: list[ModelAssetFile] = field(default_factory=list)


@dataclass(frozen=True)
class ModelInfo:
    """manifest 中 ``models[]`` 单个模型条目 — 对齐 Kotlin ``OcrModelInfo``."""

    version: str
    family: str
    display_name: str
    backbone: str
    asset_stem: str
    model_size_m: float | None
    artifacts_by_engine: dict[str, dict[str, ModelArtifact]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReleaseManifest:
    """``model-assets.json`` 顶层结构 — 对齐 Kotlin ``V2ReleaseManifest``."""

    schema_version: int
    model_count: int
    model_list: list[str]
    models: list[ModelInfo]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReleaseTag:
    """``list_release_tags`` 返回的 tag 摘要."""

    tag: str
    major: int
    minor: int
    patch: int
    source: ModelSource
    is_prerelease: bool


# =================== HTTP 辅助 ===================


def _http_get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
) -> Any:
    """GET ``url`` 并把响应体解析为 JSON. 失败抛 :class:`RuntimeError`.

    故意只使用标准库 ``urllib.request``, 避免引入 ``httpx`` 之外的依赖.
    """
    if params:
        from urllib.parse import urlencode

        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
    except urllib.error.URLError as e:
        msg = f"HTTP GET 失败: {url} ({e})"
        raise RuntimeError(msg) from e
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        msg = f"无法解析 JSON 响应: {url} ({e})"
        raise RuntimeError(msg) from e


def _http_get_bytes(
    url: str,
    dest_path: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    progress: Callable[[int, int], None] | None = None,
    chunk_size: int = 64 * 1024,
) -> None:
    """GET ``url`` 并把二进制流写入 ``dest_path``.

    ``progress`` 回调签名: ``progress(downloaded_bytes, total_bytes)``.
    ``total_bytes`` 取自 ``Content-Length``, 不存在时为 -1.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = -1
            try:
                total = int(resp.headers.get("Content-Length", "-1"))
            except (TypeError, ValueError):
                total = -1
            downloaded = 0
            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress is not None:
                        progress(downloaded, total)
    except urllib.error.URLError as e:
        msg = f"HTTP 下载失败: {url} ({e})"
        raise RuntimeError(msg) from e


def _compute_sha256(file_path: str, chunk_size: int = 64 * 1024) -> str:
    """计算文件 SHA256, 返回 64 字符小写 hex."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# =================== manifest 解析 ===================


def parse_release_manifest(json_text: str | bytes | dict[str, Any]) -> ReleaseManifest:
    """解析 ``model-assets.json`` 内容, 返回 :class:`ReleaseManifest`.

    接受 JSON 字符串、字节或已解析的 dict. 字段缺失时使用空值/默认值以保持向前兼容.
    """
    if isinstance(json_text, (bytes, bytearray)):
        root: dict[str, Any] = json.loads(json_text.decode("utf-8"))
    elif isinstance(json_text, str):
        root = json.loads(json_text)
    elif isinstance(json_text, dict):
        root = json_text
    else:
        msg = f"不支持的 manifest 类型: {type(json_text).__name__}"
        raise TypeError(msg)

    schema_version = int(root.get("schema_version") or 2)
    explicit_count = int(root.get("model_count") or 0)

    model_list_raw = root.get("modellist") or []
    model_list: list[str] = [str(s) for s in model_list_raw if s]

    raw_models = root.get("models") or []
    models: list[ModelInfo] = []
    for idx, m in enumerate(raw_models):
        if not isinstance(m, dict):
            continue
        info = _parse_model_entry(m)
        models.append(info)
        # 若顶层 modellist 缺失, 用 models[].asset_stem 补全 (与 Kotlin 端一致)
        if idx >= len(model_list) and info.asset_stem:
            model_list.append(info.asset_stem)

    model_count = explicit_count if explicit_count > 0 else len(models)
    return ReleaseManifest(
        schema_version=schema_version,
        model_count=model_count,
        model_list=model_list,
        models=models,
        raw=root,
    )


def _parse_model_entry(obj: dict[str, Any]) -> ModelInfo:
    asset_stem = str(obj.get("asset_stem") or "")
    backbone = str(obj.get("backbone") or "")
    version = str(obj.get("version") or "")
    family = str(obj.get("family") or "")
    display_name = str(obj.get("display_name") or "") or asset_stem

    model_size_m_raw = obj.get("model_size_m")
    model_size_m: float | None
    if model_size_m_raw is None:
        model_size_m = None
    else:
        try:
            model_size_m = float(model_size_m_raw)
        except (TypeError, ValueError):
            model_size_m = None

    by_engine: dict[str, dict[str, ModelArtifact]] = {}
    artifacts = obj.get("artifacts") or {}
    if isinstance(artifacts, dict):
        for engine, by_precision in artifacts.items():
            if not isinstance(by_precision, dict):
                continue
            inner: dict[str, ModelArtifact] = {}
            for precision, art in by_precision.items():
                if not isinstance(art, dict):
                    continue
                inner[precision] = _parse_artifact(art, engine, precision)
            by_engine[str(engine)] = inner

    return ModelInfo(
        version=version,
        family=family,
        display_name=display_name,
        backbone=backbone,
        asset_stem=asset_stem,
        model_size_m=model_size_m,
        artifacts_by_engine=by_engine,
        raw=obj,
    )


def _parse_artifact(
    obj: dict[str, Any],
    engine_override: str | None = None,
    precision_override: str | None = None,
) -> ModelArtifact:
    engine = engine_override or str(obj.get("engine") or "")
    precision = precision_override or str(obj.get("precision") or "")
    fmt = obj.get("format")
    fmt_str: str | None = str(fmt) if fmt else None
    files_raw = obj.get("files") or []
    files: list[ModelAssetFile] = []
    if isinstance(files_raw, list):
        for f in files_raw:
            if not isinstance(f, dict):
                continue
            path = str(f.get("path") or "")
            name = str(f.get("release_asset_name") or "") or path
            sha = f.get("sha256")
            files.append(
                ModelAssetFile(
                    path=path,
                    release_asset_name=name,
                    sha256=str(sha) if sha else None,
                )
            )
    return ModelArtifact(
        engine=engine,
        precision=precision,
        format=fmt_str,
        files=files,
    )


def find_artifact(
    manifest: ReleaseManifest,
    engine: str,
    precision: str,
) -> ModelArtifact | None:
    """在 manifest 中查找 ``(engine, precision)`` 对应的 artifact."""
    by_precision = manifest.models[0].artifacts_by_engine.get(engine) if manifest.models else None
    if by_precision is None:
        return None
    return by_precision.get(precision)


def find_artifact_in_model(
    model: ModelInfo, engine: str, precision: str
) -> ModelArtifact | None:
    """在单个 :class:`ModelInfo` 中查找 ``(engine, precision)`` artifact."""
    by_precision = model.artifacts_by_engine.get(engine)
    if by_precision is None:
        return None
    return by_precision.get(precision)


def select_artifact(
    manifest: ReleaseManifest,
    backbone: str,
    precision: str,
    asset_stem: str | None = None,
) -> tuple[ModelInfo, ModelArtifact] | None:
    """在 manifest 中按 ``(backbone[, asset_stem], precision)`` 选择 ``ncnn`` artifact.

    查找顺序 (与 Kotlin 端 ``selectV2Artifact`` 一致):
        1. asset_stem 精确匹配 → backbone 匹配
        2. 任一 backbone 匹配的第一个模型
        3. 兜底: 第一个模型

    Returns:
        ``(model_info, artifact)`` 元组, 找不到时返回 ``None``.
    """
    candidates = manifest.models
    if not candidates:
        return None

    resolved = None
    if asset_stem is not None:
        resolved = next(
            (m for m in candidates if m.asset_stem == asset_stem and m.backbone == backbone),
            None,
        )
    if resolved is None:
        resolved = next((m for m in candidates if m.backbone == backbone), None)
    if resolved is None:
        resolved = candidates[0]

    artifact = find_artifact_in_model(resolved, "ncnn", precision)
    if artifact is not None:
        return resolved, artifact

    # 兜底: 任意模型里有 ncnn + precision 命中
    for m in candidates:
        if m.backbone != backbone:
            continue
        art = find_artifact_in_model(m, "ncnn", precision)
        if art is not None:
            return m, art
    return None


# =================== manifest / 文件下载 ===================


def fetch_manifest(
    primary: ModelSource = ModelSource.GITEE,
    tag: str = DEFAULT_TAG,
    *,
    fallback: ModelSource | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[ModelSource, ReleaseManifest]:
    """下载 ``<base>/<tag>/model-assets.json``, 主源失败时回退.

    Returns:
        ``(实际成功的源, 解析后的 manifest)``.

    Raises:
        RuntimeError: 主源与 fallback 均失败.
    """
    if fallback is None:
        fallback = primary.other

    sources: list[ModelSource] = [primary, fallback]
    last_error: Exception | None = None
    for src in sources:
        url = src.file_url(tag, MANIFEST_NAME)
        try:
            payload = _http_get_json(url, timeout=timeout)
        except RuntimeError as e:
            logger.warning("从 %s 拉取 manifest 失败: %s", src.value, e)
            last_error = e
            continue
        if not isinstance(payload, dict):
            logger.warning("从 %s 拉取到非 dict 响应 (类型=%s), 跳过", src.value, type(payload).__name__)
            continue
        return src, parse_release_manifest(payload)
    msg = f"无法从 {primary.value} / {fallback.value} 拉取 manifest (tag={tag})"
    if last_error is not None:
        msg += f": {last_error}"
    raise RuntimeError(msg)


def download_file(
    url: str,
    dest_path: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    expected_sha256: str | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    """下载单个文件 (覆盖已存在). 若 ``expected_sha256`` 非空, 校验失败抛 :class:`RuntimeError`."""
    _http_get_bytes(url, dest_path, timeout=timeout, progress=progress)
    if expected_sha256:
        actual = _compute_sha256(dest_path)
        if actual.lower() != expected_sha256.lower():
            # 校验失败时删除已下载文件, 让调用方可以重试
            try:
                import os

                os.remove(dest_path)
            except OSError:
                pass
            msg = f"SHA256 校验失败: {url} (expected={expected_sha256}, actual={actual})"
            raise RuntimeError(msg)


# =================== 进度回调接口 ===================


@dataclass
class DownloadProgress:
    """下载进度事件 — 对齐 Kotlin ``DownloadProgressListener.onProgress``."""

    file_index: int
    total_files: int
    current_file_name: str
    current_file_progress: int  # 0-100
    overall_progress: int  # 0-100


ProgressCallback = Callable[[DownloadProgress], None]


def _noop_progress(_: DownloadProgress) -> None:
    return None


# =================== 顶层入口: 下载一组文件 ===================


def download_artifact(
    artifact: ModelArtifact,
    dest_dir: str,
    *,
    primary: ModelSource = ModelSource.GITEE,
    tag: str = DEFAULT_TAG,
    fallback: ModelSource | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    on_progress: ProgressCallback | None = None,
    skip_existing: bool = True,
) -> list[str]:
    """下载 :class:`ModelArtifact` 中所有文件, 主源/fallback 自动切换.

    Args:
        artifact: 来自 :func:`select_artifact` 的产物.
        dest_dir: 模型文件输出目录 (自动创建).
        primary: 主源.
        tag: release tag.
        fallback: 备选源, 默认 ``primary.other``.
        timeout: HTTP 超时.
        on_progress: 进度回调.
        skip_existing: 已存在且校验通过的文件是否跳过.

    Returns:
        实际写入到磁盘的本地文件路径列表 (按 artifact.files 顺序).

    Raises:
        RuntimeError: 任一文件在 ``MAX_DOWNLOAD_ATTEMPTS`` 次尝试后仍失败.
    """
    import os

    if fallback is None:
        fallback = primary.other

    os.makedirs(dest_dir, exist_ok=True)
    callback = on_progress or _noop_progress

    written: list[str] = []
    total = len(artifact.files)
    sources_cycle: list[ModelSource] = [primary, fallback]

    for i, asset in enumerate(artifact.files):
        dest = os.path.join(dest_dir, asset.release_asset_name)
        file_index = i + 1

        if skip_existing and os.path.exists(dest) and os.path.getsize(dest) > 0:
            if asset.sha256:
                if _compute_sha256(dest).lower() == asset.sha256.lower():
                    callback(
                        DownloadProgress(
                            file_index=file_index,
                            total_files=total,
                            current_file_name=asset.release_asset_name,
                            current_file_progress=100,
                            overall_progress=int((file_index * 100) / total),
                        )
                    )
                    written.append(dest)
                    continue
            else:
                callback(
                    DownloadProgress(
                        file_index=file_index,
                        total_files=total,
                        current_file_name=asset.release_asset_name,
                        current_file_progress=100,
                        overall_progress=int((file_index * 100) / total),
                    )
                )
                written.append(dest)
                continue

        def file_progress(downloaded: int, total_bytes: int, *, _name: str = asset.release_asset_name, _idx: int = i + 1) -> None:
            cur = 0 if total_bytes <= 0 else min(100, int(downloaded * 100 / total_bytes))
            callback(
                DownloadProgress(
                    file_index=_idx,
                    total_files=total,
                    current_file_name=_name,
                    current_file_progress=cur,
                    overall_progress=int(((_idx - 1) * 100 + cur) / total),
                )
            )

        last_error: Exception | None = None
        success = False
        for attempt in range(MAX_DOWNLOAD_ATTEMPTS):
            src = sources_cycle[attempt % len(sources_cycle)]
            url = src.file_url(tag, asset.release_asset_name)
            try:
                download_file(
                    url,
                    dest,
                    timeout=timeout,
                    expected_sha256=asset.sha256,
                    progress=file_progress,
                )
                success = True
                break
            except RuntimeError as e:
                logger.warning(
                    "下载 %s 失败 (attempt=%d source=%s): %s",
                    asset.release_asset_name,
                    attempt + 1,
                    src.value,
                    e,
                )
                last_error = e
                # 删除可能残缺的文件, 让下一轮重试
                try:
                    if os.path.exists(dest):
                        os.remove(dest)
                except OSError:
                    pass

        if not success:
            msg = (
                f"下载 {asset.release_asset_name} 在 {MAX_DOWNLOAD_ATTEMPTS} 次尝试后仍失败: "
                f"{last_error}"
            )
            raise RuntimeError(msg)

        callback(
            DownloadProgress(
                file_index=file_index,
                total_files=total,
                current_file_name=asset.release_asset_name,
                current_file_progress=100,
                overall_progress=int((file_index * 100) / total),
            )
        )
        written.append(dest)

    return written


# =================== release tag 列表/解析 ===================


def _parse_semver(tag: str) -> tuple[int, int, int] | None:
    m = SEMVER_TAG_REGEX.match(tag)
    if not m:
        return None
    try:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    except ValueError:
        return None


def _fetch_tags_from_source(source: ModelSource) -> list[ReleaseTag]:
    """从一个源拉取 release tag 列表, 转成 :class:`ReleaseTag`. 失败返回空列表."""
    try:
        payload = _http_get_json(
            source.releases_api(),
            params={"per_page": 100},
        )
    except RuntimeError as e:
        logger.warning("从 %s 拉取 release 列表失败: %s", source.value, e)
        return []
    if not isinstance(payload, list):
        return []
    out: list[ReleaseTag] = []
    for rel in payload:
        if not isinstance(rel, dict):
            continue
        if rel.get("draft"):
            continue
        if rel.get("prerelease"):
            continue
        tag_name = str(rel.get("tag_name") or "")
        semver = _parse_semver(tag_name)
        if semver is None:
            continue
        out.append(
            ReleaseTag(
                tag=tag_name,
                major=semver[0],
                minor=semver[1],
                patch=semver[2],
                source=source,
                is_prerelease=bool(rel.get("prerelease")),
            )
        )
    return out


def list_release_tags() -> list[ReleaseTag]:
    """列出所有可用 release tag, 按 (major, minor, patch) 降序.

    优先 Gitee API; Gitee 失败时回退到 GitHub.
    """
    for src in (ModelSource.GITEE, ModelSource.GITHUB):
        tags = _fetch_tags_from_source(src)
        if tags:
            tags.sort(key=lambda t: (t.major, t.minor, t.patch), reverse=True)
            return tags
    return []


def resolve_latest_tag(
    *,
    max_major: int = 2,
    max_minor: int = -1,
    min_major: int = 2,
    min_minor: int = 0,
    min_patch: int = 0,
    fallback: str = DEFAULT_TAG,
) -> str:
    """解析"最新可用" tag, Gitee API 优先, GitHub fallback.

    行为对齐 Kotlin ``ModelDownloader.resolveLatestV2Tag``:
        - 只考虑 ``v{major}.{minor}.{patch}`` 形式的稳定版 tag
        - 过滤掉低于 ``(min_major, min_minor, min_patch)`` 的 tag
        - ``max_minor < 0`` 表示不限 minor, 只锁 ``max_major``
        - 在满足 ``(max_major, max_minor)`` 约束的 tag 中选最大 patch
        - 任何阶段失败都返回 ``fallback``
    """
    unbounded_minor = max_minor < 0
    try:
        tags = list_release_tags()
    except Exception as e:  # noqa: BLE001
        logger.warning("resolve_latest_tag 失败: %s, fallback=%s", e, fallback)
        return fallback

    candidates: list[ReleaseTag] = []
    for t in tags:
        if t.major != max_major:
            continue
        if not unbounded_minor and t.minor > max_minor:
            continue
        # 过滤低于最低版本
        if t.major < min_major:
            continue
        if t.major == min_major and t.minor < min_minor:
            continue
        if t.major == min_major and t.minor == min_minor and t.patch < min_patch:
            continue
        candidates.append(t)

    if not candidates:
        logger.warning("没有匹配 v%d.x.x 的 release, fallback=%s", max_major, fallback)
        return fallback

    candidates.sort(key=lambda t: (t.major, t.minor, t.patch), reverse=True)
    return candidates[0].tag


# =================== 一站式下载入口 ===================


def download_v2_models(
    dest_dir: str,
    *,
    primary: ModelSource = ModelSource.GITEE,
    tag: str | None = None,
    backbone: str = DEFAULT_BACKBONE,
    precision: str = DEFAULT_PRECISION,
    asset_stem: str | None = None,
    on_progress: ProgressCallback | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[str]:
    """"清单 → 选 artifact → 下载" 一站式入口, 完整对齐 Kotlin ``ModelDownloader.downloadV2``.

    Args:
        dest_dir: 输出目录.
        primary: 主源, 默认 ``GITEE``.
        tag: release tag, ``None`` 时调用 :func:`resolve_latest_tag` 自动选择.
        backbone: 模型 backbone.
        precision: 精度.
        asset_stem: 精确 asset_stem 匹配 (可选).
        on_progress: 进度回调.
        timeout: HTTP 超时.

    Returns:
        下载完成的本地文件路径列表.
    """
    resolved_tag = tag or resolve_latest_tag()
    logger.info(
        "下载 v2 模型: source=%s tag=%s backbone=%s precision=%s",
        primary.value,
        resolved_tag,
        backbone,
        precision,
    )

    src, manifest = fetch_manifest(primary, resolved_tag, timeout=timeout)
    logger.info("manifest 来源: %s (model_count=%d)", src.value, manifest.model_count)

    selected = select_artifact(manifest, backbone, precision, asset_stem)
    if selected is None:
        msg = (
            f"manifest 中找不到 engine=ncnn backbone={backbone} precision={precision} 的产物"
        )
        raise RuntimeError(msg)

    return download_artifact(
        selected[1],
        dest_dir,
        primary=primary,
        tag=resolved_tag,
        timeout=timeout,
        on_progress=on_progress,
    )


__all__ = [
    # 常量
    "DEFAULT_BACKBONE",
    "DEFAULT_PRECISION",
    "DEFAULT_TAG",
    "DEFAULT_TIMEOUT",
    "GITEE_BASE_URL",
    "GITEE_RELEASES_API",
    "GITHUB_BASE_URL",
    "GITHUB_RELEASES_API",
    "MANIFEST_NAME",
    "MAX_DOWNLOAD_ATTEMPTS",
    "SEMVER_TAG_REGEX",
    # 枚举
    "ModelSource",
    # 数据类
    "DownloadProgress",
    "ModelArtifact",
    "ModelAssetFile",
    "ModelInfo",
    "ProgressCallback",
    "ReleaseManifest",
    "ReleaseTag",
    # 解析
    "find_artifact",
    "find_artifact_in_model",
    "parse_release_manifest",
    "select_artifact",
    # 下载
    "download_artifact",
    "download_file",
    "download_v2_models",
    "fetch_manifest",
    # tags
    "list_release_tags",
    "resolve_latest_tag",
]
