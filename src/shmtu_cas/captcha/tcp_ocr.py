"""通过远端 TCP OCR 服务识别验证码 — 对齐 Rust ``captcha::CaptchaOcr``."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass


@dataclass
class CaptchaOcr:
    """远端 TCP OCR 客户端 (无状态).

    协议: 把图片字节写入 TCP 流, 末尾追加 ``<END>`` 标记, 读取响应文本 (trim).
    """

    host: str
    port: int
    connect_timeout: float = 5.0
    read_timeout: float = 10.0
    write_timeout: float = 10.0

    def ocr_by_remote_tcp(self, image_data: bytes) -> str:
        """同步发送图片并读取识别结果."""
        with socket.create_connection(
            (self.host, self.port), timeout=self.connect_timeout
        ) as sock:
            sock.settimeout(self.read_timeout)
            sock.sendall(image_data)
            sock.sendall(b"<END>")

            chunks: list[bytes] = []
            while True:
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace").strip()

    def ocr_auto_retry(self, image_data: bytes, max_retries: int = 3) -> str:
        """带重试的同步 OCR; 失败抛 ``RuntimeError``."""
        last_error: Exception | None = None
        for i in range(max_retries):
            try:
                result = self.ocr_by_remote_tcp(image_data)
                if result:
                    return result
                last_error = RuntimeError("OCR返回空结果")
            except Exception as e:  # noqa: BLE001 — 统一捕获网络层异常
                last_error = e
                print(f"第{i + 1}次OCR尝试失败: {e}")
                if i < max_retries - 1:
                    time.sleep(1)
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"OCR在{max_retries}次重试后失败")
