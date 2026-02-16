"""CLI entry-point for telegram-post."""

import argparse
import pathlib
import sys

from telegram_post.client import TelegramClient, normalize_channel
from telegram_post.config import ConfigStore, JsonConfigStore, prompt_if_missing


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post a message to a Telegram channel via Bot API.",
    )
    parser.add_argument("text", nargs="?", help="Message text (inline)")
    parser.add_argument(
        "--from-file", type=pathlib.Path, help="Read message text from a file",
    )
    parser.add_argument(
        "--image",
        type=pathlib.Path,
        metavar="PATH",
        help="Send a photo (jpg/png/gif/webp, max 10 MB)",
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Telegram channel (e.g. myChannel, @myChannel, or numeric ID)",
    )
    parser.add_argument(
        "--parse-mode",
        choices=["HTML", "Markdown", "MarkdownV2"],
        help="Message parse mode",
    )
    parser.add_argument(
        "--reset-keys",
        action="store_true",
        help="Clear all saved credentials and re-prompt from scratch",
    )
    return parser.parse_args(argv)


def _read_post_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.from_file:
        return args.from_file.read_text(encoding="utf-8").strip()
    print("Enter message text (Ctrl+D to send):")
    return sys.stdin.read().strip()


def main(argv: list[str] | None = None, *, _config: ConfigStore | None = None) -> None:
    args = _parse_args(argv)
    config = _config or JsonConfigStore()

    if args.reset_keys:
        config.remove(["bot_token"])

    if not config.get("bot_token"):
        print(
            "\n"
            "First-time setup\n"
            "================\n"
            "You need a Telegram Bot Token.\n"
            "\n"
            "1. Open https://t.me/BotFather\n"
            "2. Send /newbot and follow the prompts\n"
            "3. Copy the Bot Token below\n",
        )

    bot_token = prompt_if_missing(config, "bot_token", "Bot Token")
    channel = normalize_channel(args.channel)

    if args.image:
        if not args.image.exists():
            print(f"Image not found: {args.image}", file=sys.stderr)
            sys.exit(1)

    text = _read_post_text(args) if not args.image else (args.text or "")
    if not args.image and not text:
        print("Empty message text, aborting.", file=sys.stderr)
        sys.exit(1)

    client = TelegramClient(bot_token)

    if args.image:
        caption = text or None
        if args.from_file and not args.text:
            caption = args.from_file.read_text(encoding="utf-8").strip() or None
        try:
            result = client.send_photo(
                channel, args.image, caption=caption, parse_mode=args.parse_mode,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)
    else:
        result = client.send_message(
            channel, text, parse_mode=args.parse_mode,
        )

    print(f"Message posted!\n{result.url}")
