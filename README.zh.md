# DoroPet

[繁體中文](README.md) | [English](README.en.md) | 简体中文

把 [小智](https://xiaozhi.me/) 做成一只透明桌宠。角色是 Live2D 的 Doro，窗口不挡住桌面，操作都在右键菜单。

本项目改自 [huangjunsen0406/py-xiaozhi](https://github.com/huangjunsen0406/py-xiaozhi)，使用 MIT 协议。语音、唤醒词和工具仍走原来的 Python 后端。

## 桌宠怎么用

- 左键拖动 Doro。
- 右键打开菜单：开始或结束对话、打断、连续或单次、输入消息、重新连线、设置、Discord、退出。
- 默认是连续对话。按一次「開始對話」，她说完会继续听，状态显示「聆聽中…」。再按「停止對話」才回到待命。
- 还没绑定时，会先弹出「啟用小智」，显示 6 位验证码。到 [xiaozhi.me](https://xiaozhi.me/) 添加设备并贴上验证码，完成后才会换成桌宠。
- 唤醒词默认是「你好小智」。验证码播报使用 `zh-TW` 音频。

## 下载

打开 [Actions](https://github.com/Oliver0804/DoroPet-xiaozhi/actions/workflows/build.yml)，选择 **Build & Upload Release Assets**，点击 **Run workflow**。完成后下载：

| 文件 | 平台 |
| --- | --- |
| `DoroPet-windows-x64` | Windows 安装程序（exe） |
| `DoroPet-macos-arm64` | Apple 芯片 Mac（dmg） |
| `DoroPet-macos-x64` | Intel Mac（dmg） |

推送 `v*.*.*` 标签时，同一套文件也会挂到 GitHub Release。安装包内含桌宠项目和对应平台的 Godot 4.7。

## 从源码运行

需要 Python 3.12 和 [uv](https://docs.astral.sh/uv/)。从源码运行时还要安装 [Godot 4.7](https://godotengine.org/download)。macOS 默认查找 `/Applications/Godot.app`，也可以用环境变量 `GODOT_BIN` 指定可执行文件。

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

配置文件：

- macOS：`~/Library/Application Support/py-xiaozhi/config/config.json`
- Windows：`%APPDATA%\py-xiaozhi\config\config.json`

右键「設定…」可以改麦克风、扬声器、唤醒词、回声消除、连接地址和 Discord。

## Discord 语音

在设置里贴上 Bot Token 并开启 Discord。到语音频道输入 `/doro join`。频道里有人说话会送给小智，小智的回复会播回频道。本机需要 Node.js。第一次使用请在 `discord_bridge/` 执行 `npm install`。

## 开发

```bash
uv sync --group dev --extra gui --extra live2d
uv run pytest
uv run ruff check .
```
