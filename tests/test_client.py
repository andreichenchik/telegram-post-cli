"""Unit tests for TelegramClient and CLI."""

import pathlib
from unittest.mock import MagicMock, patch

import pytest

from telegram_post.cli import main
from telegram_post.client import PostResult, TelegramClient, normalize_channel

from helpers import DictConfigStore


@pytest.fixture
def client() -> TelegramClient:
    return TelegramClient(bot_token="123:FAKE")


def _base_config() -> DictConfigStore:
    """Config with bot_token pre-filled."""
    return DictConfigStore({"bot_token": "123:FAKE"})


# --- TelegramClient.send_message ---


class TestSendMessage:
    def test_sends_correct_payload(self, client: TelegramClient) -> None:
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = _ok_response(
                {"result": {"message_id": 42}},
            )
            client.send_message("@chan", "Hello!")

            body = mock_post.call_args.kwargs["json"]
            assert body == {"chat_id": "@chan", "text": "Hello!"}

    def test_includes_parse_mode(self, client: TelegramClient) -> None:
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = _ok_response(
                {"result": {"message_id": 1}},
            )
            client.send_message("@chan", "<b>Bold</b>", parse_mode="HTML")

            body = mock_post.call_args.kwargs["json"]
            assert body["parse_mode"] == "HTML"

    def test_returns_post_result(self, client: TelegramClient) -> None:
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = _ok_response(
                {"result": {"message_id": 42}},
            )
            result = client.send_message("@mychannel", "test")
            assert isinstance(result, PostResult)
            assert result.message_id == 42
            assert result.url == "https://t.me/mychannel/42"

    def test_raises_on_400(self, client: TelegramClient) -> None:
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = _error_response(400)
            with pytest.raises(Exception):
                client.send_message("@chan", "bad")

    def test_raises_on_403(self, client: TelegramClient) -> None:
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = _error_response(403)
            with pytest.raises(Exception):
                client.send_message("@chan", "forbidden")

    def test_raises_on_429(self, client: TelegramClient) -> None:
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = _error_response(429)
            with pytest.raises(Exception):
                client.send_message("@chan", "rate limited")


# --- TelegramClient.send_photo ---


class TestSendPhoto:
    def test_uploads_photo(
        self, client: TelegramClient, tmp_path: pathlib.Path,
    ) -> None:
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"\xff\xd8" + b"\x00" * 100)
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = _ok_response(
                {"result": {"message_id": 10}},
            )
            result = client.send_photo("@chan", img)
        assert result.message_id == 10
        assert mock_post.call_args.kwargs["files"]["photo"] is not None

    def test_includes_caption(
        self, client: TelegramClient, tmp_path: pathlib.Path,
    ) -> None:
        img = tmp_path / "photo.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 100)
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = _ok_response(
                {"result": {"message_id": 11}},
            )
            client.send_photo("@chan", img, caption="Nice pic")
            data = mock_post.call_args.kwargs["data"]
            assert data["caption"] == "Nice pic"

    def test_rejects_unsupported_format(
        self, client: TelegramClient, tmp_path: pathlib.Path,
    ) -> None:
        bmp = tmp_path / "image.bmp"
        bmp.write_bytes(b"\x00" * 100)
        with pytest.raises(ValueError, match="Unsupported image format"):
            client.send_photo("@chan", bmp)

    def test_rejects_oversized_file(
        self, client: TelegramClient, tmp_path: pathlib.Path,
    ) -> None:
        big = tmp_path / "huge.png"
        big.write_bytes(b"\x00" * (10 * 1024 * 1024 + 1))
        with pytest.raises(ValueError, match="Image too large"):
            client.send_photo("@chan", big)

    def test_raises_on_api_error(
        self, client: TelegramClient, tmp_path: pathlib.Path,
    ) -> None:
        img = tmp_path / "pic.jpg"
        img.write_bytes(b"\xff\xd8" + b"\x00" * 100)
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = _error_response(400)
            with pytest.raises(Exception):
                client.send_photo("@chan", img)


# --- normalize_channel ---


class TestNormalizeChannel:
    def test_bare_name(self) -> None:
        assert normalize_channel("myChannel") == "@myChannel"

    def test_already_prefixed(self) -> None:
        assert normalize_channel("@myChannel") == "@myChannel"

    def test_numeric_string_gets_prefix(self) -> None:
        assert normalize_channel("12345") == "@12345"


# --- CLI ---


class TestCLIOutput:
    @patch("telegram_post.cli.TelegramClient")
    def test_prints_url(
        self, mock_client_cls: MagicMock,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mock_client = mock_client_cls.return_value
        mock_client.send_message.return_value = PostResult(
            message_id=42, url="https://t.me/mychan/42",
        )
        main(["--channel", "mychan", "Hello!"], _config=_base_config())
        out = capsys.readouterr().out
        assert "https://t.me/mychan/42" in out

    @patch("telegram_post.cli.TelegramClient")
    def test_sends_photo_with_caption(
        self, mock_client_cls: MagicMock,
        tmp_path: pathlib.Path,
    ) -> None:
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"\xff\xd8" + b"\x00" * 100)

        mock_client = mock_client_cls.return_value
        mock_client.send_photo.return_value = PostResult(
            message_id=55, url="https://t.me/mychan/55",
        )
        main(["--channel", "mychan", "--image", str(img), "Caption"], _config=_base_config())
        mock_client.send_photo.assert_called_once_with(
            "@mychan", img, caption="Caption", parse_mode=None,
        )

    @patch("telegram_post.cli.TelegramClient")
    def test_sends_photo_without_caption(
        self, mock_client_cls: MagicMock,
        tmp_path: pathlib.Path,
    ) -> None:
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"\xff\xd8" + b"\x00" * 100)

        mock_client = mock_client_cls.return_value
        mock_client.send_photo.return_value = PostResult(
            message_id=56, url="https://t.me/mychan/56",
        )
        main(["--channel", "mychan", "--image", str(img)], _config=_base_config())
        mock_client.send_photo.assert_called_once_with(
            "@mychan", img, caption=None, parse_mode=None,
        )

    @patch("telegram_post.cli.TelegramClient")
    def test_passes_parse_mode(
        self, mock_client_cls: MagicMock,
    ) -> None:
        mock_client = mock_client_cls.return_value
        mock_client.send_message.return_value = PostResult(
            message_id=1, url="https://t.me/ch/1",
        )
        main(["--channel", "ch", "--parse-mode", "HTML", "<b>Bold</b>"], _config=_base_config())
        mock_client.send_message.assert_called_once_with(
            "@ch", "<b>Bold</b>", parse_mode="HTML",
        )


class TestCLIValidation:
    def test_rejects_empty_text(self) -> None:
        with pytest.raises(SystemExit), patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = ""
            main(["--channel", "ch"], _config=_base_config())

    @patch("builtins.input", return_value="")
    def test_rejects_missing_bot_token(self, _input: object) -> None:
        config = DictConfigStore()
        with pytest.raises(SystemExit):
            main(["--channel", "ch", "hello"], _config=config)

    def test_rejects_missing_channel(self) -> None:
        with pytest.raises(SystemExit):
            main(["hello"], _config=_base_config())


# --- helpers ---


def _ok_response(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.ok = True
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def _error_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = False
    resp.text = "error"
    return resp
