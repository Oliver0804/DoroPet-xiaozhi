extends Node2D
## Doro Live2D。表情對照 DoroPet，嘴巴跟後端送來的音量。

const MODEL_PATH := "res://assets/doro/Doro.model3.json"
const EMOTION := {
	"neutral": "",
	"relaxed": "",
	"angry": "Exp1",
	"confused": "Exp2",
	"sad": "Exp2",
	"crying": "Exp2",
	"embarrassed": "Exp2",
	"surprised": "Exp3",
	"shocked": "Exp3",
	"thinking": "Exp7",
	"cool": "Exp5",
	"confident": "Exp5",
	"winking": "Exp5",
	"loving": "Exp6",
	"kissy": "Exp6",
	"happy": "Exp8",
	"laughing": "Exp8",
	"funny": "TongueOut",
	"silly": "TongueOut",
	"delicious": "TongueOut",
	"sleepy": "Highlight OFF",
}

var model: Node
var _params := {}
var _mouth := 0.0
var _mouth_target := 0.0
var _mouth_at := 0.0
var _smooth_dx := 0.0
var _smooth_dy := 0.0
var _idle := 0.0
var _last_mouse := Vector2.ZERO
var _blink_t := 3.0
var _blink_anim := -1.0
var _thinking := false
var _thinking_t := 0.0


func _ready() -> void:
	if not ClassDB.class_exists("GDCubismUserModel"):
		push_warning("沒有 gd_cubism，臉部維持空白")
		return
	if not ResourceLoader.exists(MODEL_PATH) and not FileAccess.file_exists(MODEL_PATH):
		push_warning("找不到 Live2D 模型: %s" % MODEL_PATH)
		return
	model = ClassDB.instantiate("GDCubismUserModel")
	model.set("assets", MODEL_PATH)
	model.set("texture_filter", CanvasItem.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS)
	add_child(model)
	_layout()
	_cache_params()
	# Idle 動作是跑步循環。桌寵只留視線、眨眼和嘴型，不要一直跑。
	if model.has_method("stop_all_motions"):
		model.call("stop_all_motions")


func _layout() -> void:
	if model == null:
		return
	var size := get_viewport_rect().size
	if size.x < 10.0:
		size = Vector2(400, 460)
	# 模型原點在中心。縮到視窗裡，頭和腳都留邊，不要裁切。
	model.scale = Vector2(0.16, 0.16)
	model.position = Vector2(size.x * 0.5, size.y * 0.56)


func set_emotion(name: String) -> void:
	var key := name.strip_edges().to_lower()
	if not EMOTION.has(key):
		return
	_thinking = key == "thinking"
	if not _thinking:
		_thinking_t = 0.0
	if model == null:
		return
	var expr: String = EMOTION[key]
	if expr == "":
		if model.has_method("stop_expression"):
			model.call("stop_expression")
		return
	if model.has_method("start_expression"):
		model.call("start_expression", expr)


func set_mouth(level: float) -> void:
	_mouth_target = clampf(level, 0.0, 1.0)
	_mouth_at = Time.get_ticks_msec() / 1000.0


func _process(dt: float) -> void:
	if model == null:
		return
	if Time.get_ticks_msec() / 1000.0 - _mouth_at > 0.12:
		_mouth_target = 0.0
	_mouth = lerpf(_mouth, _mouth_target, clampf(dt * 20.0, 0.0, 1.0))
	var gaze := _gaze(dt)
	_set_param("ParamAngleX", gaze.x * 30.0)
	_set_param("ParamAngleY", -gaze.y * 30.0)
	_set_param("ParamAngleZ", gaze.x * 9.0)
	_set_param("ParamEyeBallX", gaze.x)
	_set_param("ParamEyeBallY", -gaze.y)
	_set_param("ParamBodyAngleX", gaze.x * 10.0)
	_set_param("ParamMouthOpenY", _mouth)
	_blink(dt)


func _gaze(dt: float) -> Vector2:
	var target := Vector2.ZERO
	if _thinking:
		_thinking_t += dt
		target = Vector2(cos(_thinking_t * 3.0) * 0.7, sin(_thinking_t * 3.0) * 0.7)
	else:
		var mouse := DisplayServer.mouse_get_position()
		var moved := mouse.distance_to(_last_mouse) > 2.0
		_last_mouse = mouse
		if moved:
			_idle = 0.0
		else:
			_idle += dt
		if _idle < 3.0:
			var win := Vector2(DisplayServer.window_get_position())
			var size := Vector2(DisplayServer.window_get_size())
			var delta := Vector2(mouse) - (win + size * 0.5)
			target = Vector2(clampf(delta.x / 600.0, -1.0, 1.0), clampf(delta.y / 600.0, -1.0, 1.0))
		else:
			var t := _idle - 3.0
			target = Vector2(sin(t * 0.5) * 0.6 + sin(t * 1.3) * 0.2, sin(t * 0.7) * 0.3 + cos(t * 1.1) * 0.2)
	var k := clampf(dt * 6.0, 0.0, 1.0)
	_smooth_dx = lerpf(_smooth_dx, target.x, k)
	_smooth_dy = lerpf(_smooth_dy, target.y, k)
	return Vector2(_smooth_dx, _smooth_dy)


func _blink(dt: float) -> void:
	if _thinking:
		return
	if _blink_anim >= 0.0:
		_blink_anim += dt
		if _blink_anim >= 0.18:
			_blink_anim = -1.0
			_blink_t = randf_range(10.0, 30.0)
			_set_param("ParamEyeLOpen", 1.0)
			_set_param("ParamEyeROpen", 1.0)
			return
		var t := _blink_anim / 0.18
		var eye := absf(t * 2.0 - 1.0)
		_set_param("ParamEyeLOpen", eye)
		_set_param("ParamEyeROpen", eye)
		return
	_blink_t -= dt
	if _blink_t <= 0.0:
		_blink_anim = 0.0


func _cache_params() -> void:
	_params.clear()
	if model == null or not model.has_method("get_parameters"):
		return
	for p in model.call("get_parameters"):
		_params[str(p.id)] = p


func _set_param(id: String, value: float) -> void:
	var p = _params.get(id)
	if p != null:
		p.value = value
