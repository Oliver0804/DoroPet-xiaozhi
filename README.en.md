# DoroPet

[繁體中文](README.md) | English | [简体中文](README.zh.md)

A transparent desktop pet for [Xiaozhi](https://xiaozhi.me/). The character is a Live2D Doro. The window stays out of the way, and every control lives in the right-click menu.

This project is based on [huangjunsen0406/py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi) and stays under the MIT license. Voice, wake word, and tools still run on the original Python backend.

## Using the pet

- Drag Doro with the left mouse button.
- Right-click for the menu: start or stop a conversation, interrupt, continuous or one-shot mode, type a message, reconnect, settings, Discord, and quit.
- Continuous conversation is the default. Press **開始對話** once. After she finishes speaking she keeps listening, and the status reads **聆聽中…**. Press **停止對話** to return to standby.
- If this computer is not bound yet, an **啟用小智** window appears with a 6-digit code. Add the device at [xiaozhi.me](https://xiaozhi.me/) and paste the code. The pet opens after binding.
- The default wake word is 「你好小智」. The activation code is spoken with the `zh-TW` sound files.

## Downloads

Open [Actions](https://github.com/Oliver0804/DoroPet-xiaozhi/actions/workflows/build.yml), choose **Build & Upload Release Assets**, and click **Run workflow**. When it finishes, download:

| File | Platform |
| --- | --- |
| `DoroPet-windows-x64` | Windows installer (exe) |
| `DoroPet-macos-arm64` | Apple silicon Mac (dmg) |
| `DoroPet-macos-x64` | Intel Mac (dmg) |

Pushing a `v*.*.*` tag also attaches those files to a GitHub Release. Installers include the pet project and the Godot 4.7 editor for that platform.

## Run from source

You need Python 3.12 and [uv](https://docs.astral.sh/uv/). A source checkout also needs [Godot 4.7](https://godotengine.org/download). On macOS the app looks for `/Applications/Godot.app`. Set `GODOT_BIN` to point somewhere else.

```bash
uv sync --extra gui --extra live2d
uv run main.py
```

Other modes:

```bash
uv run main.py --mode cli
uv run main.py --mode tui    # also pass --extra tui
uv run main.py --mode gpio
```

Config files:

- macOS: `~/Library/Application Support/py-xiaozhi/config/config.json`
- Windows: `%APPDATA%\py-xiaozhi\config\config.json`

The settings window can change the microphone, speaker, wake word, echo cancellation, server URLs, and Discord.

## Discord voice

Paste a bot token in settings and turn Discord on. In a voice channel, type `/doro join`. Speech in the channel is sent to Xiaozhi, and her reply is played back in the channel. Node.js is required. Run `npm install` inside `discord_bridge/` the first time.

## Development

```bash
uv sync --group dev --extra gui --extra live2d
uv run pytest
uv run ruff check .
```
