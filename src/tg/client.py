"""Telegram Bot API client for posting messages and photos."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Protocol

import requests

_BASE_URL = "https://api.telegram.org/bot"
_SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


@dataclass(frozen=True)
class PostResult:
    """Result of posting a message to Telegram."""

    message_id: int
    url: str


class TelegramAPI(Protocol):
    """Interface for Telegram Bot API operations."""

    def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        parse_mode: str | None = None,
    ) -> PostResult:
        """Send a text message and return the result."""
        ...

    def send_photo(
        self,
        chat_id: str,
        photo_path: pathlib.Path,
        *,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> PostResult:
        """Send a photo with optional caption and return the result."""
        ...


class TelegramClient:
    """HTTP client for Telegram Bot API.

    Usage::

        client = TelegramClient(bot_token="123:ABC...")
        result = client.send_message("@mychannel", "Hello!")
    """

    def __init__(self, bot_token: str) -> None:
        self._api_url = f"{_BASE_URL}{bot_token}"
        self._session = requests.Session()

    def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        parse_mode: str | None = None,
    ) -> PostResult:
        """Send a text message to a chat/channel."""
        body: dict = {"chat_id": chat_id, "text": text}
        if parse_mode is not None:
            body["parse_mode"] = parse_mode

        resp = self._session.post(f"{self._api_url}/sendMessage", json=body)
        if not resp.ok:
            raise requests.HTTPError(
                f"{resp.status_code}: {resp.text}", response=resp,
            )
        msg = resp.json()["result"]
        return PostResult(
            message_id=msg["message_id"],
            url=_build_url(chat_id, msg["message_id"]),
        )

    def send_photo(
        self,
        chat_id: str,
        photo_path: pathlib.Path,
        *,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> PostResult:
        """Send a photo with optional caption to a chat/channel.

        Supports jpg, png, gif, webp up to 10 MB.
        Raises ``ValueError`` for unsupported format or oversized files.
        """
        _validate_image(photo_path)

        data: dict = {"chat_id": chat_id}
        if caption is not None:
            data["caption"] = caption
        if parse_mode is not None:
            data["parse_mode"] = parse_mode

        with open(photo_path, "rb") as f:
            resp = self._session.post(
                f"{self._api_url}/sendPhoto",
                data=data,
                files={"photo": f},
            )
        if not resp.ok:
            raise requests.HTTPError(
                f"{resp.status_code}: {resp.text}", response=resp,
            )
        msg = resp.json()["result"]
        return PostResult(
            message_id=msg["message_id"],
            url=_build_url(chat_id, msg["message_id"]),
        )


def normalize_channel(channel: str) -> str:
    """Normalize a public channel username for Telegram API.

    Prepends ``@`` to bare names; already-prefixed names are returned as-is.
    """
    if channel.startswith("@"):
        return channel
    return f"@{channel}"


def _validate_image(path: pathlib.Path) -> None:
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED_IMAGE_TYPES:
        raise ValueError(
            f"Unsupported image format '{suffix}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_IMAGE_TYPES))}",
        )
    size = path.stat().st_size
    if size > _MAX_IMAGE_SIZE:
        raise ValueError(
            f"Image too large ({size / 1024 / 1024:.1f} MB). "
            f"Maximum: {_MAX_IMAGE_SIZE / 1024 / 1024:.0f} MB",
        )


def _build_url(chat_id: str, message_id: int) -> str:
    return f"https://t.me/{chat_id[1:]}/{message_id}"
