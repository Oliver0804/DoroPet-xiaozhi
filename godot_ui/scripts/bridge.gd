extends Node
## 跟 Python 小智後端的一行一則 JSON。

signal message_received(data: Dictionary)

var port := 0
var _tcp := StreamPeerTCP.new()
var _raw := PackedByteArray()
var _connected := false
var _ready_sent := false


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var i := 0
	while i < args.size():
		if args[i] == "--port" and i + 1 < args.size():
			port = int(args[i + 1])
		i += 1
	if port <= 0:
		push_error("沒有收到 --port，介面無法連上小智後端")
		return
	var err := _tcp.connect_to_host("127.0.0.1", port)
	if err != OK:
		push_error("連線失敗: %s" % err)


func _process(_dt: float) -> void:
	if port <= 0:
		return
	_tcp.poll()
	var status := _tcp.get_status()
	if status == StreamPeerTCP.STATUS_CONNECTED and not _connected:
		_connected = true
		_tcp.set_no_delay(true)
	if status != StreamPeerTCP.STATUS_CONNECTED:
		return
	var available := _tcp.get_available_bytes()
	if available > 0:
		var chunk: Array = _tcp.get_data(available)
		if chunk[0] == OK:
			_raw.append_array(chunk[1])
			_drain()
	if _connected and not _ready_sent:
		_ready_sent = true
		send({"type": "ready"})


func send(data: Dictionary) -> void:
	if _tcp.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		return
	var line := JSON.stringify(data) + "\n"
	_tcp.put_data(line.to_utf8_buffer())


func _drain() -> void:
	while true:
		var nl := _raw.find(10)
		if nl < 0:
			return
		var line := _raw.slice(0, nl)
		_raw = _raw.slice(nl + 1)
		var text := line.get_string_from_utf8().strip_edges()
		if text == "":
			continue
		var parsed = JSON.parse_string(text)
		if parsed is Dictionary:
			message_received.emit(parsed)
