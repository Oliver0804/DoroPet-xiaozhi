#!/usr/bin/env bash
# 下載對應平台的 Godot 4.7 編輯器到 vendor/godot，供安裝包內啟動桌寵。
set -euo pipefail

os_name="${1:?mac|win|linux}"
arch_name="${2:-}"
dest="vendor/godot"
base="https://github.com/godotengine/godot/releases/download/4.7-stable"
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

rm -rf "$dest"
mkdir -p "$dest"

case "$os_name" in
  mac)
    asset="Godot_v4.7-stable_macos.universal.zip"
    ;;
  win)
    asset="Godot_v4.7-stable_win64.exe.zip"
    ;;
  linux)
    if [ "$arch_name" = "arm64" ]; then
      asset="Godot_v4.7-stable_linux.arm64.zip"
    else
      asset="Godot_v4.7-stable_linux.x86_64.zip"
    fi
    ;;
  *)
    echo "未知平台: $os_name" >&2
    exit 1
    ;;
esac

echo "下載 $asset"
curl -fL --retry 3 -o "$workdir/godot.zip" "$base/$asset"
unzip -q "$workdir/godot.zip" -d "$dest"

if [ "$os_name" = "win" ]; then
  exe="$(find "$dest" -type f -name '*.exe' | head -1)"
  if [ -z "$exe" ]; then
    echo "zip 裡沒有 exe" >&2
    exit 1
  fi
  cp "$exe" "$dest/Godot.exe"
fi

if [ "$os_name" = "linux" ]; then
  bin="$(find "$dest" -type f -name 'Godot*' ! -name '*.zip' | head -1)"
  if [ -n "$bin" ]; then
    chmod +x "$bin"
    cp "$bin" "$dest/godot"
  fi
fi

find "$dest" -maxdepth 2 -type d -o -type f | head -20
echo "Godot 已放到 $dest"
