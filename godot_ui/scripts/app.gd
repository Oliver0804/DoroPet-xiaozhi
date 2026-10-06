extends Control
## 小智主畫面與裝置啟用。字串用臺灣繁體。

const FACE_SCRIPT := preload("res://scripts/face.gd")

var _role := "main"
var _activation: Control
var _main: Control
var _status: Label
var _chat: Label
var _music: Label
var _talk: Button
var _mode: Button
var _line: LineEdit
var _code: Label
var _hint: Label
var _face: Node2D
var _auto := true
var _url := "https://xiaozhi.me/"
var _shot_saved := false
var _background: ColorRect
var _chrome: Array[Control] = []
var _menu: PopupMenu
var _dragging := false
var _drag_offset := Vector2.ZERO
var _settings: Window
var _input_window: Window
var _discord: Node
var _discord_status := "Discord 未開啟"
var _settings_form := {}


func _ready() -> void:
	set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	theme = _make_theme()
	_background = ColorRect.new()
	_background.color = Color("F7F8FA")
	_background.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	_background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_background)
	_role = _arg("--role", "main")
	_build_activation()
	_build_main()
	_build_menu()
	_build_settings_window()
	_build_input_window()
	_discord = preload("res://scripts/discord_link.gd").new()
	_discord.status_changed.connect(func(text: String) -> void:
		_discord_status = text
		_rebuild_menu()
	)
	add_child(_discord)
	_show_role(_role)
	get_tree().root.close_requested.connect(_on_close)
	Bridge.message_received.connect(_on_message)


func _arg(name: String, fallback: String) -> String:
	var args := OS.get_cmdline_user_args()
	var i := 0
	while i < args.size():
		if args[i] == name and i + 1 < args.size():
			return args[i + 1]
		i += 1
	return fallback


func _on_close() -> void:
	Bridge.send({"type": "quit"})
	get_tree().quit()


func _on_message(msg: Dictionary) -> void:
	match str(msg.get("type", "")):
		"phase":
			_show_role(str(msg.get("name", "main")))
		"activation":
			_apply_activation(msg)
		"state":
			_apply_state(msg)
		"mouth":
			if _face:
				_face.set_mouth(float(msg.get("level", 0.0)))
		"settings":
			_fill_settings(msg.get("data", {}))
		"settings_saved":
			_discord_status = "設定已儲存"
			_rebuild_menu()
		"discord_speak":
			if _discord:
				_discord.speak_wav_b64(str(msg.get("wav_b64", "")))
		"discord_config":
			if _discord:
				_discord.set_config(str(msg.get("url", "")), str(msg.get("token", "")))
				_discord.set_enabled(bool(msg.get("enabled", false)))
		"quit":
			get_tree().quit()


func _show_role(role: String) -> void:
	_role = role
	_activation.visible = role == "activation"
	_main.visible = role != "activation"
	_apply_window_mode(role != "activation")
	if role == "activation":
		DisplayServer.window_set_title("啟用小智")
	else:
		DisplayServer.window_set_title("小智")


func _apply_activation(msg: Dictionary) -> void:
	_show_role("activation")
	if str(msg.get("url", "")) != "":
		_url = str(msg.get("url"))
	_code.text = str(msg.get("code", "------"))
	var status := str(msg.get("status", "waiting"))
	if status == "ok":
		_hint.text = "啟用完成，正在打開主畫面…"
	elif status == "error":
		_hint.text = str(msg.get("message", "啟用失敗，請再試一次"))
	else:
		_hint.text = "請到 xiaozhi.me 新增裝置，貼上驗證碼。完成前這個視窗會一直等。"
	var serial := str(msg.get("serial", ""))
	var mac := str(msg.get("mac", ""))
	if serial != "" or mac != "":
		_hint.text += "\n序號 %s    MAC %s" % [serial, mac]


func _apply_state(msg: Dictionary) -> void:
	_show_role("main")
	var connected := bool(msg.get("connected", false))
	var status := str(msg.get("status", "待命"))
	_status.text = status
	_status.add_theme_color_override("font_color", Color("00B42A") if connected else Color("F53F3F"))
	var said := str(msg.get("chat", ""))
	_chat.text = said
	_chat.visible = said != ""
	_music.text = str(msg.get("music", ""))
	_music.visible = _music.text != ""
	var button := str(msg.get("button", ""))
	if button != "":
		_talk.text = button
	_auto = bool(msg.get("auto_mode", false))
	_rebuild_menu()
	if _face and msg.has("emotion"):
		_face.set_emotion(str(msg.get("emotion", "neutral")))
	var shot := _arg("--snapshot", "")
	if shot != "" and not _shot_saved:
		_shot_saved = true
		get_tree().create_timer(0.8).timeout.connect(func() -> void:
			var image := get_viewport().get_texture().get_image()
			image.save_png(shot)
		)


func _build_activation() -> void:
	_activation = _page()
	add_child(_activation)
	var box := _column(_activation)
	box.add_child(_title("啟用小智"))
	_code = _label("------", 36, Color("F53F3F"))
	_code.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(_code)
	_hint = _label("", 15, Color("4E5969"))
	_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(_hint)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	box.add_child(row)
	var copy := _button("複製驗證碼", false)
	copy.pressed.connect(func() -> void:
		DisplayServer.clipboard_set(_code.text)
		Bridge.send({"type": "copy_code"})
	)
	var open := _button("打開啟用頁面", true)
	open.pressed.connect(func() -> void:
		OS.shell_open(_url)
		Bridge.send({"type": "open_url"})
	)
	row.add_child(copy)
	row.add_child(open)
	copy.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	open.size_flags_horizontal = Control.SIZE_EXPAND_FILL


func _build_main() -> void:
	_main = _page()
	add_child(_main)
	var box := _column(_main)
	var header := HBoxContainer.new()
	_chrome.append(header)
	header.add_theme_constant_override("separation", 12)
	box.add_child(header)
	header.add_child(_title("小智"))
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(spacer)
	var quit := _button("關閉", false)
	quit.pressed.connect(_on_close)
	header.add_child(quit)

	_face = FACE_SCRIPT.new()
	_face.z_index = 1
	add_child(_face)

	_chat = _label("待命", 16, Color("1D2129"))
	_chat.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_chat.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_chat.custom_minimum_size = Vector2(0, 36)
	_chat.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_chat.add_theme_color_override("font_outline_color", Color.WHITE)
	_chat.add_theme_constant_override("outline_size", 6)
	box.add_child(_chat)
	_music = _label("", 13, Color("86909C"))
	_music.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_music.visible = false
	box.add_child(_music)
	_status = _label("待命", 14, Color("4E5969"))
	_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_status.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_status.add_theme_color_override("font_outline_color", Color.WHITE)
	_status.add_theme_constant_override("outline_size", 4)
	box.add_child(_status)

	var composer := HBoxContainer.new()
	_chrome.append(composer)
	composer.add_theme_constant_override("separation", 8)
	box.add_child(composer)
	_line = LineEdit.new()
	_line.placeholder_text = "輸入訊息，按 Enter 送出"
	_line.custom_minimum_size = Vector2(0, 40)
	_line.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var field := StyleBoxFlat.new()
	field.bg_color = Color.WHITE
	field.border_color = Color("E5E6EB")
	field.set_border_width_all(1)
	field.set_corner_radius_all(10)
	field.content_margin_left = 12
	field.content_margin_right = 12
	field.content_margin_top = 8
	field.content_margin_bottom = 8
	_line.add_theme_stylebox_override("normal", field)
	_line.add_theme_stylebox_override("focus", field)
	_line.add_theme_color_override("font_color", Color("1D2129"))
	_line.add_theme_color_override("font_placeholder_color", Color("86909C"))
	_line.add_theme_color_override("caret_color", Color("165DFF"))
	_line.text_submitted.connect(func(text: String) -> void:
		_send_text(text)
	)
	composer.add_child(_line)
	var send := _button("送出", true)
	send.pressed.connect(func() -> void:
		_send_text(_line.text)
	)
	composer.add_child(send)

	var actions := HBoxContainer.new()
	_chrome.append(actions)
	actions.add_theme_constant_override("separation", 8)
	box.add_child(actions)
	_talk = _button("開始對話", true)
	_talk.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_talk.pressed.connect(func() -> void:
		if _auto:
			Bridge.send({"type": "auto_start"})
		else:
			Bridge.send({"type": "manual_toggle"})
	)
	actions.add_child(_talk)
	var abort := _button("打斷", false)
	abort.pressed.connect(func() -> void:
		Bridge.send({"type": "abort"})
	)
	actions.add_child(abort)
	_mode = _button("連續對話", false)
	_mode.pressed.connect(func() -> void:
		Bridge.send({"type": "auto_toggle"})
	)
	actions.add_child(_mode)


func _apply_window_mode(pet: bool) -> void:
	var win := get_window()
	win.borderless = pet
	win.transparent = pet
	win.always_on_top = pet
	_background.visible = not pet
	for node in _chrome:
		node.visible = not pet
	if pet:
		DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, true)
		DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_TRANSPARENT, true)
		DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_ALWAYS_ON_TOP, true)
		DisplayServer.window_set_size(Vector2i(400, 460))
		get_viewport().transparent_bg = true
		RenderingServer.set_default_clear_color(Color(0, 0, 0, 0))
		if _face and _face.has_method("_layout"):
			_face.call_deferred("_layout")
		if _settings:
			_settings.hide()
		if _input_window:
			_input_window.hide()
	else:
		DisplayServer.window_set_size(Vector2i(520, 420))
		RenderingServer.set_default_clear_color(Color("F7F8FA"))


func _show_menu_at_mouse() -> void:
	# 視窗沒有嵌進主畫面時，選單座標是螢幕絕對位置，要跟滑鼠而不是視窗內部座標。
	_menu.reset_size()
	var pos := DisplayServer.mouse_get_position()
	_menu.position = pos
	_menu.popup()
	_menu.position = pos


func _build_menu() -> void:
	_menu = PopupMenu.new()
	_menu.id_pressed.connect(_on_menu)
	add_child(_menu)
	_rebuild_menu()


func _rebuild_menu() -> void:
	if _menu == null:
		return
	_menu.clear()
	_menu.add_item(_talk.text if _talk else "開始對話", 1)
	_menu.add_item("打斷", 2)
	_menu.add_item("單次說話" if _auto else "連續對話", 3)
	_menu.add_separator()
	_menu.add_item("輸入訊息…", 4)
	_menu.add_item("重新連線", 7)
	_menu.add_item("設定…", 5)
	_menu.add_separator()
	_menu.add_item(_discord_status, 6)
	_menu.add_item("結束", 9)


func _on_menu(id: int) -> void:
	match id:
		1:
			if _auto:
				Bridge.send({"type": "auto_start"})
			else:
				Bridge.send({"type": "manual_toggle"})
		2:
			Bridge.send({"type": "abort"})
		3:
			Bridge.send({"type": "auto_toggle"})
		4:
			if _input_window:
				_input_window.popup_centered(Vector2i(420, 120))
		7:
			_status.text = "重新連線中…"
			Bridge.send({"type": "reconnect"})
		5:
			Bridge.send({"type": "open_settings"})
			if _settings:
				_settings.popup_centered(Vector2i(520, 640))
		6:
			Bridge.send({"type": "discord_toggle"})
		9:
			_on_close()


func _build_input_window() -> void:
	_input_window = Window.new()
	_input_window.title = "跟小智說"
	_input_window.size = Vector2i(420, 140)
	_input_window.transparent = false
	_input_window.borderless = false
	_input_window.always_on_top = true
	_input_window.close_requested.connect(_input_window.hide)
	var box := VBoxContainer.new()
	box.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	box.add_theme_constant_override("separation", 8)
	_input_window.add_child(box)
	var edit := LineEdit.new()
	edit.placeholder_text = "輸入訊息，按 Enter 送出"
	edit.text_submitted.connect(func(text: String) -> void:
		_send_text(text)
		edit.text = ""
		_input_window.hide()
	)
	box.add_child(edit)
	var send := _button("送出", true)
	send.pressed.connect(func() -> void:
		_send_text(edit.text)
		edit.text = ""
		_input_window.hide()
	)
	box.add_child(send)
	_input_window.visible = false
	add_child(_input_window)
	_input_window.hide()


func _build_settings_window() -> void:
	_settings = Window.new()
	_settings.title = "設定"
	_settings.size = Vector2i(520, 640)
	_settings.transparent = false
	_settings.borderless = false
	_settings.always_on_top = true
	_settings.close_requested.connect(_settings.hide)
	var root := VBoxContainer.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("separation", 8)
	_settings.add_child(root)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root.add_child(scroll)
	var form := VBoxContainer.new()
	form.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	form.add_theme_constant_override("separation", 8)
	scroll.add_child(form)
	_settings_form["box"] = form
	var save := _button("儲存", true)
	save.pressed.connect(_save_settings)
	root.add_child(save)
	_settings.visible = false
	add_child(_settings)
	_settings.hide()


func _fill_settings(data: Dictionary) -> void:
	var form: VBoxContainer = _settings_form.get("box")
	if form == null:
		return
	for child in form.get_children():
		form.remove_child(child)
		child.free()
	_settings_form["data"] = data
	form.add_child(_title("音訊"))
	_settings_form["input"] = _option_row(form, "麥克風", data.get("input_devices", []), str(data.get("input_device", "")))
	_settings_form["output"] = _option_row(form, "喇叭", data.get("output_devices", []), str(data.get("output_device", "")))
	form.add_child(_title("喚醒詞"))
	_settings_form["wake_on"] = _check_row(form, "使用喚醒詞", bool(data.get("wake_word_enabled", true)))
	_settings_form["wake"] = _edit_row(form, "喚醒詞", str(data.get("wake_word", "你好小智")))
	form.add_child(_title("連線"))
	_settings_form["aec"] = _check_row(form, "回聲消除", bool(data.get("aec_enabled", false)))
	_settings_form["ota"] = _edit_row(form, "註冊介面", str(data.get("ota_url", "")))
	_settings_form["ws"] = _edit_row(form, "WebSocket", str(data.get("websocket_url", "")))
	form.add_child(_title("Discord 語音"))
	var hint := _label("在頻道打 /doro join 把小智叫進去。Token 只存在這台電腦。", 12, Color("86909C"))
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	form.add_child(hint)
	_settings_form["dc_on"] = _check_row(form, "開啟 Discord", bool(data.get("discord_enabled", false)))
	_settings_form["dc_token"] = _edit_row(form, "Bot Token", str(data.get("discord_token", "")))
	_settings_form["dc_url"] = _edit_row(form, "橋接位址", str(data.get("discord_url", "ws://127.0.0.1:8765")))
	form.add_child(_title("快捷鍵"))
	for item in data.get("shortcuts", []):
		form.add_child(_label("%s    %s" % [item.get("label", ""), item.get("keys", "")], 14, Color("4E5969")))


func _save_settings() -> void:
	var data: Dictionary = _settings_form.get("data", {})
	var input_names: Array = data.get("input_devices", [])
	var output_names: Array = data.get("output_devices", [])
	var input_box: OptionButton = _settings_form.get("input")
	var output_box: OptionButton = _settings_form.get("output")
	Bridge.send({
		"type": "save_settings",
		"data": {
			"input_device": input_names[input_box.selected] if input_box and input_box.selected >= 0 and input_box.selected < input_names.size() else "",
			"output_device": output_names[output_box.selected] if output_box and output_box.selected >= 0 and output_box.selected < output_names.size() else "",
			"wake_word_enabled": (_settings_form["wake_on"] as CheckBox).button_pressed,
			"wake_word": (_settings_form["wake"] as LineEdit).text,
			"aec_enabled": (_settings_form["aec"] as CheckBox).button_pressed,
			"ota_url": (_settings_form["ota"] as LineEdit).text,
			"websocket_url": (_settings_form["ws"] as LineEdit).text,
			"discord_enabled": (_settings_form["dc_on"] as CheckBox).button_pressed,
			"discord_token": (_settings_form["dc_token"] as LineEdit).text,
			"discord_url": (_settings_form["dc_url"] as LineEdit).text,
		},
	})
	_settings.hide()


func _option_row(parent: Node, caption: String, items: Array, current: String) -> OptionButton:
	var row := HBoxContainer.new()
	parent.add_child(row)
	row.add_child(_label(caption, 14, Color("4E5969")))
	var box := OptionButton.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var selected := 0
	for i in items.size():
		box.add_item(str(items[i]))
		if str(items[i]) == current:
			selected = i
	if items.size() > 0:
		box.select(selected)
	row.add_child(box)
	return box


func _edit_row(parent: Node, caption: String, value: String) -> LineEdit:
	var row := HBoxContainer.new()
	parent.add_child(row)
	row.add_child(_label(caption, 14, Color("4E5969")))
	var edit := LineEdit.new()
	edit.text = value
	edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	if caption == "Bot Token":
		edit.secret = true
	row.add_child(edit)
	return edit


func _check_row(parent: Node, caption: String, on: bool) -> CheckBox:
	var box := CheckBox.new()
	box.text = caption
	box.button_pressed = on
	parent.add_child(box)
	return box


func _input(event: InputEvent) -> void:
	if _role != "main":
		return
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
		_show_menu_at_mouse()
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			_dragging = true
			_drag_offset = Vector2(DisplayServer.mouse_get_position() - DisplayServer.window_get_position())
		else:
			_dragging = false


func _process(_dt: float) -> void:
	if not _dragging:
		return
	if not Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
		_dragging = false
		return
	var pos := DisplayServer.mouse_get_position() - Vector2i(_drag_offset)
	DisplayServer.window_set_position(pos)


func _send_text(text: String) -> void:
	var body := text.strip_edges()
	if body == "":
		return
	Bridge.send({"type": "send_text", "text": body})
	_line.text = ""


func _page() -> Control:
	var page := MarginContainer.new()
	page.set_anchors_and_offsets_preset(PRESET_FULL_RECT)
	page.add_theme_constant_override("margin_left", 20)
	page.add_theme_constant_override("margin_top", 16)
	page.add_theme_constant_override("margin_right", 20)
	page.add_theme_constant_override("margin_bottom", 16)
	return page


func _column(parent: Node) -> VBoxContainer:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	parent.add_child(box)
	return box


func _title(text: String) -> Label:
	return _label(text, 22, Color("1D2129"))


func _label(text: String, size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	return label


func _button(text: String, primary: bool) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(88, 40)
	var normal := StyleBoxFlat.new()
	var hover := StyleBoxFlat.new()
	var pressed := StyleBoxFlat.new()
	if primary:
		normal.bg_color = Color("165DFF")
		hover.bg_color = Color("4080FF")
		pressed.bg_color = Color("0E42D2")
		button.add_theme_color_override("font_color", Color.WHITE)
		button.add_theme_color_override("font_hover_color", Color.WHITE)
		button.add_theme_color_override("font_pressed_color", Color.WHITE)
	else:
		normal.bg_color = Color.WHITE
		hover.bg_color = Color("F2F3F5")
		pressed.bg_color = Color("E5E6EB")
		normal.border_color = Color("E5E6EB")
		hover.border_color = Color("E5E6EB")
		pressed.border_color = Color("C9CDD4")
		for box in [normal, hover, pressed]:
			box.set_border_width_all(1)
		button.add_theme_color_override("font_color", Color("1D2129"))
	for box in [normal, hover, pressed]:
		box.set_corner_radius_all(10)
		box.content_margin_left = 14
		box.content_margin_right = 14
	button.add_theme_stylebox_override("normal", normal)
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_stylebox_override("pressed", pressed)
	button.add_theme_stylebox_override("focus", normal)
	return button


func _make_theme() -> Theme:
	var theme := Theme.new()
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["PingFang TC", "PingFang HK", "Heiti TC"])
	theme.default_font = font
	theme.default_font_size = 16
	var panel := StyleBoxFlat.new()
	panel.bg_color = Color("F7F8FA")
	theme.set_stylebox("panel", "Panel", panel)
	return theme
