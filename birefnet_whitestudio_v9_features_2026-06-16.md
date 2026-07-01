# WhiteStudio v9 功能更新 — 2026-06-16

## 更新内容

### 1. 新增 20cm×25cm @300ppi 输出尺寸预设

- 像素计算：20cm ÷ 2.54 × 300 = **2362 px**，25cm ÷ 2.54 × 300 = **2953 px**
- 位置：`app/main.py` `SIZE_PRESETS` 列表，紧排在 "20×25cm @200ppi" 之后
- 标签：`"相片"`，显示名：`"20 × 25 cm @300 ppi (打印级)"`

### 2. 新增字距（letter_spacing）调节

**worker.py（推理核心）**：
- `ProcessParams` 新增 `letter_spacing: int = 0` 字段
- `_overlay_text()` 重写：`letter_spacing > 0` 时逐字符绘制（Pillow 原生不支持字距），每字符间隔加 `letter_spacing` px
- `letter_spacing = 0`（默认）时走原整段绘制路径，性能不受影响

**main.py（GUI）**：
- 字号滑块后新增 `sld_letter_spacing` 滑块（0–60 px，默认 0）
- `_collect_params()` 自动收集 `p.letter_spacing`

### 3. 识别"华文细黑"（STXihei）字体

用户通过右键安装的华文细黑实际路径：
```
C:\Users\23107\AppData\Local\Microsoft\Windows\Fonts\STXIHEI.ttf
```

**worker.py**：
- `_load_font()` 的 `font_dirs` 新增 `%LOCALAPPDATA%\Microsoft\Windows\Fonts`（用户字体目录）
- `FONT_ALIASES` 新增 `"华文细黑": ["stxihei", "xihei"]` 和 `"STXihei": ["stxihei", "xihei"]`

**main.py**：
- `_populate_font_combo()` 的 `priority_keywords` 新增 `"华文细黑"`, `"STXihei"`, `"XIHEI"`，确保在字体下拉框中优先显示

## 测试结果

```
Test 1 - letter_spacing default: 0 (expected: 0)     ✅
Test 2a - FONT_ALIASES has 华文细黑: True            ✅
Test 2b - FONT_ALIASES has STXihei: True             ✅
Test 2c - user font dir in font_dirs: True           ✅
Test 3a - _overlay_text has letter_spacing: True     ✅
Test 3b - _overlay_text has char_widths: True        ✅
Test 4 - 华文细黑 loaded: True                       ✅
Test 5 - 20x25cm @300ppi = 2362x2953 px             ✅
```

## 待办

- 重新打包 v9 EXE（`onedir` 模式）供用户实际测试
