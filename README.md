# telegram-post-cli

CLI utility for posting messages to Telegram channels via Bot API.

## Prerequisites

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Copy the `Bot Token`
3. Add the bot as an **administrator** to your public channel

## Install & run

```bash
# Run directly (no install needed)
uvx telegram-post-cli@latest --channel myChannel "Hello Telegram!"

# Or install globally
uv tool install telegram-post-cli
```

On first run the tool will prompt for your Bot Token and save it to
`~/.config/telegram-post-cli/config.json`.

## Usage

```bash
# Inline text
telegram-post-cli --channel myChannel "Hello Telegram!"

# With image
telegram-post-cli --channel myChannel --image photo.jpg "Caption"

# Image without caption
telegram-post-cli --channel myChannel --image photo.jpg

# From file
telegram-post-cli --channel myChannel --from-file draft.txt

# With parse mode
telegram-post-cli --channel myChannel --parse-mode HTML "<b>Bold</b>"

# Interactive input (Ctrl+D to send)
telegram-post-cli --channel myChannel

# Clear saved credentials and re-prompt
telegram-post-cli --channel myChannel --reset-keys "Hello again!"
```

The `--channel` flag accepts a channel username (with or without `@`).

## Tests

```bash
uv run pytest
```
