# telegram-post

CLI utility for posting messages to Telegram channels via Bot API.

## Prerequisites

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Copy the `Bot Token`
3. Add the bot as an **administrator** to your public channel

## Setup

```bash
cp .env.example .env
# Fill in BOT_TOKEN
```

## Usage

```bash
# Inline text
uv run telegram-post --channel myChannel "Hello Telegram!"

# With image
uv run telegram-post --channel myChannel --image photo.jpg "Caption"

# Image without caption
uv run telegram-post --channel myChannel --image photo.jpg

# From file
uv run telegram-post --channel myChannel --from-file draft.txt

# With parse mode
uv run telegram-post --channel myChannel --parse-mode HTML "<b>Bold</b>"

# Interactive input (Ctrl+D to send)
uv run telegram-post --channel myChannel
```

The `--channel` flag accepts a channel username (with or without `@`).

## Tests

```bash
uv run pytest
```
