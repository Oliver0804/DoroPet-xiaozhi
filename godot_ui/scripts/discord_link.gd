extends Node
## 接 Doro 那套 discord_bridge。語音進來轉給小智，小智的聲音再送回頻道。

signal status_changed(text: String)

const DEFAULT_URL := "ws://127.0.0.1:8765"

var _ws: WebSocketPeer
var _url := DEFAULT_URL
var _token := ""
var _enabled := false
var _was_open := false
var _reconnect_at := 0
var _sidecar_pid := -1


func set_config(url: String, token: String) -> void:
	if url != "":
		_url = url
	_token = token


func set_enabled(on: bool) -> void:
	if _enabled == on:
		return
	_enabled = on
	set_process(true)
	if on:
		_connect_now()
		status_changed.emit("正在連接 Discord…")
	else:
		_close()
		status_changed.emit("Discord 已關閉")


func speak_wav_b64(wav_b64: String) -> void:
	if _ws == null or _ws.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return
	_ws.send_text(JSON.stringify({"type": "speak", "wav_b64": wav_b64}))


func _process(_dt: float) -> void:
	if not _enabled:
		return
	if _ws == null:
		if _reconnect_at > 0 and Time.get_ticks_msec() >= _reconnect_at:
			_reconnect_at = 0
			_connect_now()
		return
	_ws.poll()
	var state := _ws.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		if not _was_open:
			_was_open = true
			status_changed.emit("Discord 橋已連上")
			if _token != "":
				_ws.send_text(JSON.stringify({"type": "login", "token": _token}))
		while _ws.get_available_packet_count() > 0:
			_handle(_ws.get_packet())
	elif state == WebSocketPeer.STATE_CLOSED:
		if not _was_open:
			_spawn_sidecar()
		_close()
		_reconnect_at = Time.get_ticks_msec() + 3000


func _connect_now() -> void:
	_ws = WebSocketPeer.new()
	_ws.inbound_buffer_size = 4 << 20
	_ws.outbound_buffer_size = 4 << 20
	var err := _ws.connect_to_url(_url)
	if err != OK:
		_ws = null
		_spawn_sidecar()
		_reconnect_at = Time.get_ticks_msec() + 3000


func _close() -> void:
	if _ws != null:
		_ws.close()
		_ws = null
	_was_open = false


func _handle(raw: PackedByteArray) -> void:
	var parsed = JSON.parse_string(raw.get_string_from_utf8())
	if not parsed is Dictionary:
		return
	match str(parsed.get("type", "")):
		"login_result":
			if bool(parsed.get("ok", false)):
				status_changed.emit("Discord 已登入 %s" % str(parsed.get("bot", "")))
			else:
				status_changed.emit("Discord 登入失敗")
		"joined":
			status_changed.emit("已進入語音，召喚者 %s" % str(parsed.get("invoker_name", "")))
		"left":
			status_changed.emit("已離開語音頻道")
		"speech":
			var wav := str(parsed.get("wav_b64", ""))
			if wav == "":
				return
			Bridge.send({
				"type": "discord_wav",
				"user_name": str(parsed.get("user_name", "")),
				"wav_b64": wav,
			})


func _spawn_sidecar() -> void:
	var script_path := ProjectSettings.globalize_path("res://").path_join("../discord_bridge/index.js")
	if not FileAccess.file_exists(script_path):
		status_changed.emit("找不到 discord_bridge")
		return
	if _sidecar_pid > 0 and OS.is_process_running(_sidecar_pid):
		return
	var node_bin := "node"
	_sidecar_pid = OS.create_process(node_bin, [script_path])
	if _sidecar_pid <= 0:
		status_changed.emit("沒有啟動 node，Discord 橋起不來")
