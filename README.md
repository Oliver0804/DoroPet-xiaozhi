# DoroPet

繁體中文 | [English](README.en.md) | [简体中文](README.zh.md)

把 [小智](https://xiaozhi.me/) 做成一隻透明桌寵。角色是 Live2D 的 Doro，視窗不擋桌面，操作都在右鍵選單。

這個專案改自 [huangjunsen0406/py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi)，採用 MIT 授權。語音、喚醒詞和工具仍走原本的 Python 後端。

## 桌寵怎麼用

- 左鍵拖曳 Doro。
- 右鍵打開選單：開始或結束對話、打斷、連續或單次、輸入訊息、重新連線、設定、Discord、結束。
- 連續對話是預設。按一次「開始對話」，她講完會繼續聽，狀態顯示「聆聽中…」。再按「停止對話」才回到「待命」。
- 還沒綁定時，會先跳出「啟用小智」，顯示 6 位數驗證碼。到 [xiaozhi.me](https://xiaozhi.me/) 新增裝置並貼上驗證碼，完成後才會換成桌寵。
- 喚醒詞預設是「你好小智」。驗證碼播報使用 `zh-TW` 音檔。

## 下載

到 [Actions](https://github.com/Oliver0804/DoroPet-xiaozhi/actions/workflows/build.yml) 開啟 **Build & Upload Release Assets**，按 **Run workflow**。完成後下載：

| 檔案 | 平台 |
| --- | --- |
| `DoroPet-windows-x64` | Windows 安裝程式（exe） |
| `DoroPet-macos-arm64` | Apple 晶片 Mac（dmg） |
| `DoroPet-macos-x64` | Intel Mac（dmg） |

推上 `v*.*.*` 標籤時，同一套檔案也會掛到 GitHub Release。安裝包內含桌寵專案與對應平台的 Godot 4.7。

## 從原始碼執行

需要 Python 3.12 和 [uv](https://docs.astral.sh/uv/)。從原始碼跑時，還要安裝 [Godot 4.7](https://godotengine.org/download)，macOS 預設會找 `/Applications/Godot.app`。也可以用環境變數 `GODOT_BIN` 指定執行檔。

```bash
uv sync --extra gui --extra live2d
uv run main.py
```

其他模式：

```bash
uv run main.py --mode cli
uv run main.py --mode tui    # 需再加 --extra tui
uv run main.py --mode gpio
```

設定檔在：

- macOS：`~/Library/Application Support/py-xiaozhi/config/config.json`
- Windows：`%APPDATA%\py-xiaozhi\config\config.json`

右鍵「設定…」可以改麥克風、喇叭、喚醒詞、回聲消除、連線網址和 Discord。

## Discord 語音

在設定裡貼上 Bot Token 並開啟 Discord。到語音頻道輸入 `/doro join`，頻道裡有人說話會送給小智，小智的回覆會播回頻道。本機需安裝 Node.js。第一次使用請在 `discord_bridge/` 執行 `npm install`。

## 開發

```bash
uv sync --group dev --extra gui --extra live2d
uv run pytest
uv run ruff check .
```
