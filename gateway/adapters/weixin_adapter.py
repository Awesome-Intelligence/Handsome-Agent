# 🚪 Access - 🚪 Gateway - 微信适配器
# 🏃 Execution - 🛠️ ToolExec - 接入 iLink Bot API

"""
Weixin adapter - 微信个人号适配器
通过 iLink Bot API 长轮询接收消息，支持文本/媒体收发
依赖: aiohttp, cryptography
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import secrets
import struct
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    import aiohttp

    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    CRYPTO_AVAILABLE = True
except ImportError:
    default_backend = None
    Cipher = None
    CRYPTO_AVAILABLE = False

from ..gateway import BaseAdapter, BaseGateway, GatewayConfig
from ..message import StandardMessage, MessageChannel, MessageContent

logger = logging.getLogger(__name__)

ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
ILINK_APP_ID = "bot"
CHANNEL_VERSION = "2.2.0"

EP_GET_UPDATES = "ilink/bot/getupdates"
EP_SEND_MESSAGE = "ilink/bot/sendmessage"
EP_GET_BOT_QR = "ilink/bot/get_bot_qrcode"
EP_GET_QR_STATUS = "ilink/bot/get_qrcode_status"

LONG_POLL_TIMEOUT_MS = 35_000
API_TIMEOUT_MS = 15_000
QR_TIMEOUT_MS = 35_000

ITEM_TEXT = 1
ITEM_IMAGE = 2
ITEM_VOICE = 3
ITEM_FILE = 4
ITEM_VIDEO = 5

MSG_TYPE_USER = 1
MSG_TYPE_BOT = 2
MSG_STATE_FINISH = 2

ILINK_APP_CLIENT_VERSION = (2 << 16) | (2 << 8) | 0

# ponytail: hardcoded defaults — move to config/env when needed
DEFAULT_DM_POLICY = "open"
MAX_MESSAGE_LENGTH = 2000


def _safe_id(value: Optional[str], keep: int = 8) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "?"
    return raw[:keep] if len(raw) > keep else raw


def _json_dumps(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _random_wechat_uin() -> str:
    value = struct.unpack(">I", secrets.token_bytes(4))[0]
    return base64.b64encode(str(value).encode("utf-8")).decode("ascii")


def _base_info() -> dict:
    return {"channel_version": CHANNEL_VERSION}


def _headers(token: Optional[str], body: str) -> dict:
    h = {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "Content-Length": str(len(body.encode("utf-8"))),
        "X-WECHAT-UIN": _random_wechat_uin(),
        "iLink-App-Id": ILINK_APP_ID,
        "iLink-App-ClientVersion": str(ILINK_APP_CLIENT_VERSION),
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def _api_post(
    session: aiohttp.ClientSession,
    base_url: str,
    endpoint: str,
    payload: dict,
    token: Optional[str],
    timeout_ms: int,
) -> dict:
    body = _json_dumps({**payload, "base_info": _base_info()})
    url = f"{base_url.rstrip('/')}/{endpoint}"

    async def _do() -> dict:
        async with session.post(url, data=body, headers=_headers(token, body)) as resp:
            raw = await resp.text()
            if not resp.ok:
                raise RuntimeError(
                    f"iLink POST {endpoint} HTTP {resp.status}: {raw[:200]}"
                )
            return json.loads(raw)

    return await asyncio.wait_for(_do(), timeout=timeout_ms / 1000)


async def _get_updates(
    session: aiohttp.ClientSession,
    base_url: str,
    token: str,
    sync_buf: str,
    timeout_ms: int,
) -> dict:
    try:
        return await _api_post(
            session,
            base_url=base_url,
            endpoint=EP_GET_UPDATES,
            payload={"get_updates_buf": sync_buf},
            token=token,
            timeout_ms=timeout_ms,
        )
    except asyncio.TimeoutError:
        return {"ret": 0, "msgs": [], "get_updates_buf": sync_buf}


async def _send_message(
    session: aiohttp.ClientSession,
    base_url: str,
    token: str,
    to: str,
    text: str,
    context_token: Optional[str],
    client_id: str,
) -> dict:
    if not text or not text.strip():
        raise ValueError("_send_message: text must not be empty")
    msg: dict = {
        "from_user_id": "",
        "to_user_id": to,
        "client_id": client_id,
        "message_type": MSG_TYPE_BOT,
        "message_state": MSG_STATE_FINISH,
        "item_list": [{"type": ITEM_TEXT, "text_item": {"text": text}}],
    }
    if context_token:
        msg["context_token"] = context_token
    return await _api_post(
        session,
        base_url=base_url,
        endpoint=EP_SEND_MESSAGE,
        payload={"msg": msg},
        token=token,
        timeout_ms=API_TIMEOUT_MS,
    )


async def qr_login(
    hermes_home: str,
    bot_type: str = "3",
    timeout_seconds: int = 480,
) -> Optional[dict]:
    """交互式 QR 登录，返回凭证或 None"""
    if not AIOHTTP_AVAILABLE:
        raise RuntimeError("aiohttp is required for Weixin QR login")

    async with aiohttp.ClientSession(trust_env=True) as session:
        try:
            qr_resp = await _api_post(
                session,
                ILINK_BASE_URL,
                f"{EP_GET_BOT_QR}?bot_type={bot_type}",
                {},
                None,
                QR_TIMEOUT_MS,
            )
        except Exception as exc:
            logger.error("weixin: failed to fetch QR code: %s", exc)
            return None

        qrcode_value = str(qr_resp.get("qrcode") or "")
        qrcode_url = str(qr_resp.get("qrcode_img_content") or "")
        if not qrcode_value:
            logger.error("weixin: QR response missing qrcode")
            return None

        qr_scan_data = qrcode_url if qrcode_url else qrcode_value
        print("\n请使用微信扫描以下二维码：")
        if qrcode_url:
            print(qrcode_url)
        try:
            import qrcode

            qr = qrcode.QRCode()
            qr.add_data(qr_scan_data)
            qr.make(fit=True)
            qr.print_ascii(invert=True)
        except Exception as _qr_exc:
            print(f"（终端二维码渲染失败: {_qr_exc}，请直接打开上面的二维码链接）")

        deadline = time.monotonic() + timeout_seconds

        while time.monotonic() < deadline:
            try:
                status_resp = await _api_post(
                    session,
                    ILINK_BASE_URL,
                    f"{EP_GET_QR_STATUS}?qrcode={qrcode_value}",
                    {},
                    None,
                    QR_TIMEOUT_MS,
                )
            except asyncio.TimeoutError:
                await asyncio.sleep(1)
                continue
            except Exception as exc:
                logger.warning("weixin: QR poll error: %s", exc)
                await asyncio.sleep(1)
                continue

            status = str(status_resp.get("status") or "wait")
            if status == "wait":
                print(".", end="", flush=True)
            elif status == "scaned":
                print("\n已扫码，请在微信里确认...")
            elif status == "confirmed":
                account_id = str(status_resp.get("ilink_bot_id") or "")
                token = str(status_resp.get("bot_token") or "")
                base_url = str(status_resp.get("baseurl") or ILINK_BASE_URL)
                user_id = str(status_resp.get("ilink_user_id") or "")
                if not account_id or not token:
                    logger.error(
                        "weixin: QR confirmed but credential payload was incomplete"
                    )
                    return None
                print(f"\n微信连接成功，account_id={account_id}")
                return {
                    "account_id": account_id,
                    "token": token,
                    "base_url": base_url,
                    "user_id": user_id,
                }
            elif status == "expired":
                print("\n二维码已过期，请重新执行登录。")
                return None
            await asyncio.sleep(1)

        print("\n微信登录超时。")
        return None


class WeixinAdapter(BaseAdapter):
    """微信个人号适配器"""

    def __init__(
        self,
        gateway: BaseGateway,
        config: GatewayConfig,
        account_id: str = "",
        token: str = "",
        base_url: str = ILINK_BASE_URL,
        dm_policy: str = DEFAULT_DM_POLICY,
    ):
        super().__init__(gateway, MessageChannel.WEIXIN)
        self.account_id = account_id
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.dm_policy = dm_policy
        self.name = f"weixin-{_safe_id(account_id, keep=8)}"
        self._poll_session: Optional[aiohttp.ClientSession] = None
        self._send_session: Optional[aiohttp.ClientSession] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._running = False
        self._context_tokens: dict[str, str] = {}

    def check_requirements(self) -> bool:
        return AIOHTTP_AVAILABLE

    async def start(self) -> None:
        if not self.check_requirements():
            self.logger.error("Weixin adapter requires aiohttp: pip install aiohttp")
            return
        if not self.token or not self.account_id:
            self.logger.warning(
                "Weixin adapter: token or account_id not set, skipping start"
            )
            return

        self._poll_session = aiohttp.ClientSession(trust_env=True)
        self._send_session = aiohttp.ClientSession(trust_env=True)
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop(), name="weixin-poll")
        self.logger.info(
            "[%s] Connected account=%s base=%s",
            self.name,
            _safe_id(self.account_id),
            self.base_url,
        )

    async def stop(self) -> None:
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        if self._poll_session and not self._poll_session.closed:
            await self._poll_session.close()
        if self._send_session and not self._send_session.closed:
            await self._send_session.close()
        self.logger.info("[%s] Disconnected", self.name)

    async def _poll_loop(self) -> None:
        assert self._poll_session is not None
        sync_buf = ""
        timeout_ms = LONG_POLL_TIMEOUT_MS

        while self._running:
            try:
                resp = await _get_updates(
                    self._poll_session,
                    base_url=self.base_url,
                    token=self.token,
                    sync_buf=sync_buf,
                    timeout_ms=timeout_ms,
                )

                ret = resp.get("ret", 0)
                errcode = resp.get("errcode", 0)
                if ret not in {0, None} or errcode not in {0, None}:
                    self.logger.warning(
                        "[%s] getUpdates ret=%s errcode=%s", self.name, ret, errcode
                    )
                    await asyncio.sleep(5)
                    continue

                new_sync_buf = str(resp.get("get_updates_buf") or "")
                if new_sync_buf:
                    sync_buf = new_sync_buf

                for msg in resp.get("msgs") or []:
                    asyncio.create_task(self._process_message(msg))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.logger.error("[%s] poll error: %s", self.name, exc)
                await asyncio.sleep(5)

    async def _process_message(self, msg: dict) -> None:
        try:
            sender_id = str(msg.get("from_user_id") or "").strip()
            if not sender_id or sender_id == self.account_id:
                return

            context_token = str(msg.get("context_token") or "").strip()
            if context_token:
                self._context_tokens[sender_id] = context_token

            item_list = msg.get("item_list") or []
            text = self._extract_text(item_list)

            source = self._build_source(sender_id)
            std_msg = StandardMessage(
                channel=MessageChannel.WEIXIN,
                user_id=sender_id,
                session_id=sender_id,
                content=MessageContent(type="text", text=text),
                metadata={"raw_message": msg},
            )
            self.logger.info("[%s] inbound from=%s", self.name, _safe_id(sender_id))
            response = await self.gateway._handle_message(std_msg)
            await self.send(response)
        except Exception as exc:
            self.logger.error("[%s] inbound error: %s", self.name, exc, exc_info=True)

    def _extract_text(self, item_list: list) -> str:
        for item in item_list:
            if item.get("type") == ITEM_TEXT:
                text = str((item.get("text_item") or {}).get("text") or "")
                return text
        return ""

    def _build_source(self, user_id: str) -> str:
        return user_id

    async def send(self, message: StandardMessage) -> StandardMessage:
        if not self._send_session or not self.token:
            return message

        chat_id = message.user_id
        text = message.content.text or ""
        context_token = self._context_tokens.get(chat_id)

        try:
            chunks = self._split_text(text)
            for idx, chunk in enumerate(chunks):
                client_id = f"agentz-weixin-{uuid.uuid4().hex}"
                await _send_message(
                    self._send_session,
                    base_url=self.base_url,
                    token=self.token,
                    to=chat_id,
                    text=chunk,
                    context_token=context_token,
                    client_id=client_id,
                )
                if idx < len(chunks) - 1:
                    await asyncio.sleep(1.5)
            self.logger.info(
                "[%s] sent to=%s chunks=%d", self.name, _safe_id(chat_id), len(chunks)
            )
        except Exception as exc:
            self.logger.error(
                "[%s] send failed to=%s: %s", self.name, _safe_id(chat_id), exc
            )

        return message

    def _split_text(self, content: str) -> list[str]:
        if not content:
            return []
        if len(content) <= MAX_MESSAGE_LENGTH:
            return [content]
        # ponytail: naive split — upgrade to block-aware splitting
        return [
            content[i : i + MAX_MESSAGE_LENGTH]
            for i in range(0, len(content), MAX_MESSAGE_LENGTH)
        ]

    async def receive(self) -> StandardMessage:
        raise NotImplementedError("Weixin uses long-poll, receive() not used")
