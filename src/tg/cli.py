"""CLI entry-point for telegram-post."""

import argparse
import os
import pathlib
import sys

import dotenv

from tg.client import TelegramClient, normalize_channel

_ENV_PATH = pathlib.Path.cwd() / ".env"


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
    return parser.parse_args(argv)


def _read_post_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text
    if args.from_file:
        return args.from_file.read_text(encoding="utf-8").strip()
    print("Enter message text (Ctrl+D to send):")
    return sys.stdin.read().strip()


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    dotenv.load_dotenv(_ENV_PATH)

    bot_token = os.getenv("BOT_TOKEN", "")
    if not bot_token:
        print("BOT_TOKEN must be set in .env", file=sys.stderr)
        sys.exit(1)

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
