


"""
WhiteStudio - 三栏 PySide6 GUI
- 左：文件列表（缩略图 + 文件名 + 状态）
- 中：参数设置（核心参数 + 滑块 + 数字标签 + 文字开关）
- 右：实时日志
- 底部：工具栏 + 状态栏
"""


from __future__ import annotations
import os
import sys
import time
import traceback
import queue
import threading
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

# 强制 UTF-8（避免 Windows 控制台乱码）
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from PySide6.QtCore import Qt, QSize, QThread, Signal, QObject, QTimer, QMargins, QSettings
from PySide6.QtGui import (
    QAction, QIcon, QPixmap, QImage, QFont, QColor, QPalette, QPainter,
    QFontDatabase
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QListWidget, QListWidgetItem,
    QSlider, QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit, QComboBox,
    QGroupBox, QPlainTextEdit, QSplitter, QStatusBar, QToolBar,
    QFormLayout, QGridLayout, QSizePolicy, QScrollArea, QFrame,
    QColorDialog, QMessageBox, QProgressBar
)

import os as _appdir, sys as _appsys
_appdir_here = _appdir.path.dirname(_appdir.path.abspath(__file__))
if _appdir_here not in _appsys.path:
    _appsys.path.insert(0, _appdir_here)

import worker
from worker import ProcessParams, BIREFNET_MODELS


# ---------------------------------------------------------------------------
# 信号总线
# ---------------------------------------------------------------------------
class LogBus(QObject):
    """UI 线程日志总线（worker 跨线程 emit）"""
    log = Signal(str, str)   # level, text
    progress = Signal(int, int, str)  # current, total, filename


# ---------------------------------------------------------------------------
# 滑块 + 数字标签组件
# ---------------------------------------------------------------------------
class LabeledSlider(QWidget):
    """水平滑块，右侧带数字标签（同步显示）"""
    valueChanged = Signal(int)

    def __init__(self, label: str, minimum: int, maximum: int, value: int,
                 suffix: str = "", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 左侧文字
        self.label = QLabel(label)
        self.label.setMinimumWidth(72)
        layout.addWidget(self.label)

        # 滑块
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.slider.setMinimumWidth(140)
        layout.addWidget(self.slider, 1)

        # 数字标签
        self.value_label = QLabel(f"{value}{suffix}")
        self.value_label.setMinimumWidth(56)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.value_label.setStyleSheet(
            "QLabel { background:#f0f3f7; border:1px solid #d0d7de;"
            " padding:2px 6px; border-radius:4px; color:#1f2937; font-weight:600; }"
        )
        layout.addWidget(self.value_label)

        self.slider.valueChanged.connect(self._on_change)

    def _on_change(self, v: int):
        self.value_label.setText(f"{v}{self.suffix}")
        self.valueChanged.emit(v)

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, v: int):
        self.slider.setValue(v)

    def setRange(self, mn: int, mx: int):
        self.slider.setRange(mn, mx)

    def setSuffix(self, s: str):
        self.suffix = s
        self.value_label.setText(f"{self.slider.value()}{s}")


class LabeledDoubleSlider(QWidget):
    """支持小数的滑块（步长 0.05）"""
    valueChanged = Signal(float)

    def __init__(self, label: str, minimum: float, maximum: float, value: float,
                 step: float = 0.05, suffix: str = "", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self._step = step
        self._min = minimum
        self._max = maximum
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.label = QLabel(label)
        self.label.setMinimumWidth(72)
        layout.addWidget(self.label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(minimum / step), int(maximum / step))
        self.slider.setValue(int(value / step))
        self.slider.setMinimumWidth(140)
        layout.addWidget(self.slider, 1)

        self.value_label = QLabel(f"{value:.2f}{suffix}")
        self.value_label.setMinimumWidth(56)
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.value_label.setStyleSheet(
            "QLabel { background:#f0f3f7; border:1px solid #d0d7de;"
            " padding:2px 6px; border-radius:4px; color:#1f2937; font-weight:600; }"
        )
        layout.addWidget(self.value_label)

        self.slider.valueChanged.connect(self._on_change)

    def _on_change(self, v: int):
        f = v * self._step
        self.value_label.setText(f"{f:.2f}{self.suffix}")
        self.valueChanged.emit(f)

    def value(self) -> float:
        return self.slider.value() * self._step

    def setValue(self, v: float):
        self.slider.setValue(int(v / self._step))


# ---------------------------------------------------------------------------
# 文件列表项
# ---------------------------------------------------------------------------
class FileItemWidget(QWidget):
    # 跨线程信号：子线程发，主线程接
    _thumb_ready = Signal(str)      # 临时文件路径
    _thumb_failed = Signal(str)     # 错误信息

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)

        # 缩略图（懒加载）
        self.thumb = QLabel()
        self.thumb.setFixedSize(56, 56)
        self.thumb.setStyleSheet(
            "QLabel { background:#f3f4f6; border:1px solid #e5e7eb; border-radius:4px; }"
        )
        self.thumb.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.thumb)

        # 文件名 + 状态
        info = QVBoxLayout()
        info.setSpacing(2)
        self.name_label = QLabel(os.path.basename(path))
        self.name_label.setStyleSheet("QLabel { color:#111827; font-weight:600; }")
        self.name_label.setWordWrap(False)
        self.name_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info.addWidget(self.name_label)

        try:
            with Image.open(path) as im:
                w, h = im.size
                size_kb = os.path.getsize(path) / 1024
                meta = f"{w}×{h} · {size_kb:.1f} KB"
        except Exception:
            meta = "?"
        self.meta_label = QLabel(meta)
        self.meta_label.setStyleSheet("QLabel { color:#6b7280; font-size:11px; }")
        info.addWidget(self.meta_label)

        self.status_label = QLabel("⏳ 待处理")
        self.status_label.setStyleSheet("QLabel { color:#6b7280; font-size:11px; }")
        info.addWidget(self.status_label)

        layout.addLayout(info, 1)
        self._thumb_loaded = False
        # 连接跨线程信号 -> 槽（自动以 QueuedConnection 在 UI 线程上执行）
        self._thumb_ready.connect(self._load_thumb_from_path)
        self._thumb_failed.connect(self._set_thumb_err)
        # 异步加载缩略图
        QTimer.singleShot(0, self._load_thumb_async)

    def _load_thumb_async(self):
        """在后台线程加载缩略图（避免阻塞 UI）
        跨线程通信用 QObject signal：子线程 emit -> 主线程连接以 QueuedConnection
        """
        def work():
            try:
                with Image.open(self.path) as im:
                    im.thumbnail((96, 96))
                    im2 = im.convert("RGB") if im.mode != "RGB" else im.copy()
                    import tempfile
                    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                    tmp.close()
                    im2.save(tmp.name, "PNG", optimize=False)
                    tmp_path = tmp.name
                # 跨线程传递：signal 会自动以 QueuedConnection 调度到接收者所在线程
                self._thumb_ready.emit(tmp_path)
            except Exception as e:
                import traceback as _tb
                err = str(e) + " | " + _tb.format_exc(limit=2)
                self._thumb_failed.emit(err)
        threading.Thread(target=work, daemon=True).start()

    def _load_thumb_from_path(self, tmp_path: str):
        """在 UI 线程从临时文件加载 QImage -> QPixmap"""
        try:
            from PySide6.QtGui import QImageReader
            reader = QImageReader(tmp_path)
            reader.setAutoTransform(True)
            qimg = reader.read()
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            if qimg.isNull():
                self._set_thumb_err("QImageReader 加载为空")
                return
            pix = QPixmap.fromImage(qimg)
            self._set_thumb(pix)
        except Exception as e:
            self._set_thumb_err(str(e))

    def _set_thumb_err(self, msg: str):
        self.thumb.setText("❓")
        self.thumb.setStyleSheet(
            "QLabel { background:#fef2f2; border:1px solid #fecaca; border-radius:4px; color:#b91c1c; }"
        )
        # 调试：发送错误到日志
        if hasattr(self, 'bus') and self.bus:
            try:
                self.bus.log.emit("WARN", f"缩略图失败: {os.path.basename(self.path)} ({msg})")
            except Exception:
                pass

    def _set_thumb(self, pix: QPixmap):
        self.thumb.setPixmap(
            pix.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def set_status(self, text: str, color: str = "#6b7280"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"QLabel {{ color:{color}; font-size:11px; }}")


# ---------------------------------------------------------------------------
# 后台 worker
# ---------------------------------------------------------------------------
class ProcessWorker(QThread):
    """处理线程：通过 LogBus 报告进度/日志"""

    def __init__(self, items: List[str], dst_dir: str, model_key: str,
                 params: ProcessParams, input_size: int, log_bus: LogBus,
                 cache_dir: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.items = items
        self.dst_dir = dst_dir
        self.model_key = model_key
        self.params = params
        self.input_size = input_size
        self.cache_dir = cache_dir
        self.bus = log_bus
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        total = len(self.items)
        for i, path in enumerate(self.items, 1):
            if self._stop_flag:
                self.bus.log.emit("WARN", f"用户已停止，已处理 {i-1}/{total}")
                break
            name = os.path.basename(path)
            self.bus.log.emit("INFO", f"[{i}/{total}] 处理 {name} ...")
            self.bus.progress.emit(i - 1, total, name)
            try:
                res = worker.process_one(
                    src_path=path,
                    dst_dir=self.dst_dir,
                    model_key=self.model_key,
                    params=self.params,
                    input_size=self.input_size,
                    cache_dir=self.cache_dir,
                )
                if res["ok"]:
                    self.bus.log.emit(
                        "INFO",
                        f"  ✓ {name} → {os.path.basename(res['out'])} "
                        f"({res['inference_ms']:.0f}ms, 主体 {res['subject_size']})"
                    )
                else:
                    self.bus.log.emit("ERROR", f"  ✗ {name} 失败: {res.get('error','')}")
            except Exception as e:
                self.bus.log.emit("ERROR", f"  ✗ {name} 异常: {e}")
                traceback.print_exc()
            self.bus.progress.emit(i, total, name)
        self.bus.log.emit("INFO", f"任务完成（{total} 张）")


# ---------------------------------------------------------------------------
# PIL.Image 兼容
# ---------------------------------------------------------------------------
try:
    from PIL import Image
except Exception:
    Image = None


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WhiteStudio · BiRefNet 一键批量扣图加白底")
        self.setMinimumSize(QSize(1200, 760))
        self.resize(QSize(1400, 820))

        # 数据
        self.file_items: List[str] = []
        self.output_dir: str = str(Path.cwd() / "output")
        self.params = ProcessParams()
        self.bus = LogBus()
        self.worker: Optional[ProcessWorker] = None

        # 启动时初始化
        self._build_ui()
        self._connect()
        # 恢复上次会话的用户参数（所有滑块/复选框/下拉框/输出目录）
        self._load_settings()
        self.bus.log.emit("INFO", "WhiteStudio 就绪。")
        self.bus.log.emit("INFO", f"模型权重: {list(BIREFNET_MODELS.keys())}")
        self.bus.log.emit("INFO", f"默认输出目录: {self.output_dir}")

    # ---------------- UI 构建 ----------------
    def _build_ui(self):
        # 工具栏
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        act_add_files = QAction("➕ 添加文件", self)
        act_add_files.triggered.connect(self.act_add_files)
        toolbar.addAction(act_add_files)

        act_add_folder = QAction("📁 添加文件夹", self)
        act_add_folder.triggered.connect(self.act_add_folder)
        toolbar.addAction(act_add_folder)

        toolbar.addSeparator()
        act_clear = QAction("🗑 清空列表", self)
        act_clear.triggered.connect(self.act_clear)
        toolbar.addAction(act_clear)

        toolbar.addSeparator()
        self.act_outdir = QAction(f"📤 输出目录: {self.output_dir}", self)
        self.act_outdir.triggered.connect(self.act_choose_outdir)
        toolbar.addAction(self.act_outdir)

        toolbar.addSeparator()
        act_start = QAction("▶ 开始处理", self)
        act_start.triggered.connect(self.act_start)
        toolbar.addAction(act_start)
        self.act_start_action = act_start

        act_stop = QAction("⏹ 停止", self)
        act_stop.triggered.connect(self.act_stop)
        toolbar.addAction(act_stop)
        self.act_stop_action = act_stop

        # 中央三栏
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        main_layout.addWidget(splitter)

        # ===== 左：文件列表 =====
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(6, 6, 6, 6)
        lv.setSpacing(6)
        lv.addWidget(QLabel("📋 文件列表"))
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { background:#ffffff; border:1px solid #e5e7eb;"
            " border-radius:6px; }"
            "QListWidget::item { padding:0; border-bottom:1px solid #f1f5f9; }"
            "QListWidget::item:selected { background:#eef2ff; }"
        )
        lv.addWidget(self.list_widget, 1)

        # 左下统计
        self.left_summary = QLabel("共 0 张图片")
        self.left_summary.setStyleSheet("color:#4b5563;")
        lv.addWidget(self.left_summary)

        splitter.addWidget(left)

        # ===== 中：参数设置 =====
        middle = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(middle)
        mv = QVBoxLayout(middle)
        mv.setContentsMargins(10, 10, 10, 10)
        mv.setSpacing(10)

        title = QLabel("⚙ 参数设置")
        title.setStyleSheet("font-size:14px; font-weight:700; color:#1f2937;")
        mv.addWidget(title)

        # ---- 模型选择 ----
        gb_model = QGroupBox("模型")
        fm = QFormLayout(gb_model)
        self.cmb_model = QComboBox()
        for k in BIREFNET_MODELS:
            self.cmb_model.addItem(k, k)
        self.cmb_model.setCurrentText("general")
        fm.addRow("权重选择:", self.cmb_model)

        self.sld_input_size = LabeledSlider("输入尺寸", 512, 2048, 1024, " px")
        fm.addRow(self.sld_input_size)
        mv.addWidget(gb_model)

        # ---- 画布与裁切 ----
        gb_canvas = QGroupBox("画布与裁切")
        gc = QFormLayout(gb_canvas)

        # 输出尺寸预设（常见打印/证件/照片尺寸）
        # 格式: 显示名 -> (宽px, 高px, DPI, 标签)
        self.SIZE_PRESETS = [
            ("自定义", 0, 0, 0, ""),
            # 打印/冲印（200 ppi = 质量与体积平衡）
            ("15 × 18.75 cm @200 ppi (证件)", 1181, 1476, 200, "证件"),
            ("20 × 25 cm @200 ppi", 1575, 1969, 200, "相片"),
            ("20 × 25 cm @300 ppi (打印级)", 2362, 2953, 300, "相片"),
            ("A4 (21×29.7cm) @200 ppi", 1654, 2339, 200, "A4"),
            ("A5 (14.8×21cm) @200 ppi", 1165, 1654, 200, "A5"),
            ("5 寸 (3.5×5 寸) @300 ppi", 1050, 1500, 300, "5寸"),
            ("6 寸 (4×6 寸) @300 ppi", 1200, 1800, 300, "6寸"),
            ("7 寸 (5×7 寸) @300 ppi", 1500, 2100, 300, "7寸"),
            # 证件照（300 ppi = 打印锐利）
            ("1 寸照 (2.5×3.5cm) @300 ppi", 295, 413, 300, "1寸"),
            ("2 寸照 (3.5×4.9cm) @300 ppi", 413, 579, 300, "2寸"),
            ("小 1 寸 (2.2×3.2cm) @300 ppi", 260, 378, 300, "小1寸"),
            ("大 1 寸 (3.3×4.8cm) @300 ppi", 390, 567, 300, "大1寸"),
            # 头像/社交
            ("头像 1:1 @300 ppi (800×800)", 800, 800, 300, "头像"),
            ("朋友圈 4:3 @200 ppi (1080×810)", 1080, 810, 200, "朋友圈"),
            ("朋友圈 3:4 @200 ppi (1080×1440)", 1080, 1440, 200, "朋友圈"),
        ]
        self.cmb_size_preset = QComboBox()
        for name, _, _, _, _ in self.SIZE_PRESETS:
            self.cmb_size_preset.addItem(name)
        self.cmb_size_preset.currentIndexChanged.connect(self._on_size_preset_changed)
        gc.addRow("输出尺寸预设:", self.cmb_size_preset)

        self.sld_canvas_w = LabeledSlider("画布宽度", 256, 4096, 1024, " px")
        self.sld_canvas_h = LabeledSlider("画布高度", 256, 4096, 1024, " px")
        # 用户手动改滑块时 -> 切到"自定义"
        self.sld_canvas_w.valueChanged.connect(self._on_canvas_changed)
        self.sld_canvas_h.valueChanged.connect(self._on_canvas_changed)
        gc.addRow(self.sld_canvas_w)
        gc.addRow(self.sld_canvas_h)

        self.sld_padding = LabeledSlider("边距", 0, 512, 64, " px")
        gc.addRow(self.sld_padding)

        self.chk_center = QCheckBox("主体居中裁切（推荐）")
        self.chk_center.setChecked(True)
        gc.addRow(self.chk_center)

        self.chk_whitebg = QCheckBox("白底合成（取消 = 透明 PNG）")
        self.chk_whitebg.setChecked(True)
        gc.addRow(self.chk_whitebg)
        mv.addWidget(gb_canvas)

        # ---- 文字叠加 ----
        gb_text = QGroupBox("文字叠加（主体下方）")
        gt = QFormLayout(gb_text)
        self.chk_text = QCheckBox("启用文字叠加")
        self.chk_text.setChecked(True)
        gt.addRow(self.chk_text)

        self.sld_text_size = LabeledSlider("字号", 12, 120, 36, " px")
        gt.addRow(self.sld_text_size)

        self.sld_letter_spacing = LabeledSlider("字距", 0, 60, 0, " px")
        self.sld_letter_spacing.setToolTip("文字字符间距，0=默认。Pillow 逐字绘制。")
        gt.addRow(self.sld_letter_spacing)

        # 文字带高度: 主体/底边与文字之间的留白 px，0=紧贴
        # 同时支持"自动"——特殊值 -1（GUI 用一个独立勾选框控制）
        self.sld_text_band = LabeledSlider("文字带高度", 0, 200, 24, " px")
        self.sld_text_band.setToolTip(
            "文字与主体/画布边之间的留白距离，0=紧贴。\n勾选下方“自动”后将根据字号自动计算。"
        )
        gt.addRow(self.sld_text_band)

        self.chk_text_band_auto = QCheckBox("文字带高度自动（= max(8, 字号/2)）")
        self.chk_text_band_auto.setChecked(False)
        gt.addRow(self.chk_text_band_auto)

        h_color = QHBoxLayout()
        self.btn_text_color = QPushButton("■ 文字颜色")
        self.btn_text_color.setStyleSheet("background:#111827; color:#fff; padding:4px 8px;")
        self.btn_text_color.clicked.connect(self._pick_text_color)
        self.lbl_text_color = QLabel("#000000")
        h_color.addWidget(self.btn_text_color)
        h_color.addWidget(self.lbl_text_color)
        h_color.addStretch()
        w_color_wrap = QWidget()
        w_color_wrap.setLayout(h_color)
        gt.addRow("文字颜色:", w_color_wrap)

        self.cmb_text_pos = QComboBox()
        self.cmb_text_pos.addItems(["底部 (bottom)", "顶部 (top)"])
        gt.addRow("文字位置:", self.cmb_text_pos)

        # 字体下拉框: 自动列出 Windows 系统所有已安装 CJK + 拉丁字体
        self.cmb_text_font = QComboBox()
        self.cmb_text_font.setToolTip("默认优先微软雅黑(msyh.ttc), 也可指定其他系统字体或自定义 .ttf/.ttc 路径")
        self._populate_font_combo()
        gt.addRow("字体:", self.cmb_text_font)

        mv.addWidget(gb_text)

        # ---- 输出 ----
        gb_out = QGroupBox("输出")
        go = QFormLayout(gb_out)
        self.ed_template = QLineEdit("")
        self.ed_template.setToolTip(
            "可用占位符: {stem} (无后缀文件名)  {name} (原文件名)  {w} {h} (画布尺寸)"
        )
        go.addRow("文件名模板:", self.ed_template)

        self.cmb_format = QComboBox()
        self.cmb_format.addItems([
            "PNG (透明可选/支持白底)",
            "JPG (白底/小体积)",
            "JPEG (白底/小体积)"
        ])
        go.addRow("输出格式:", self.cmb_format)

        self.sld_quality = LabeledSlider("JPEG 质量", 50, 100, 95, "")
        go.addRow(self.sld_quality)

        self.cmb_device = QComboBox()
        self.cmb_device.addItem("GPU (CUDA)", "cuda")
        self.cmb_device.addItem("CPU", "cpu")
        go.addRow("推理设备:", self.cmb_device)

        mv.addWidget(gb_out)
        mv.addStretch()

        splitter.addWidget(scroll)

        # ===== 右：实时日志 =====
        right = QWidget()
        right.setMinimumWidth(360)  # 避免标题"实时日志"被 splitter 截断为"实"
        rv = QVBoxLayout(right)
        rv.setContentsMargins(6, 6, 6, 6)
        rv.setSpacing(6)
        lbl_log_title = QLabel("🪵 实时日志")
        lbl_log_title.setMinimumWidth(80)
        rv.addWidget(lbl_log_title)

        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet(
            "QPlainTextEdit { background:#0d1117; color:#c9d1d9; border:1px solid #30363d;"
            " border-radius:6px; font-family:'Consolas','Cascadia Mono','Menlo',monospace;"
            " font-size:11px; padding:8px; }"
        )
        rv.addWidget(self.txt_log, 1)

        h_log_btn = QHBoxLayout()
        btn_clear_log = QPushButton("清空日志")
        btn_clear_log.clicked.connect(lambda: self.txt_log.clear())
        h_log_btn.addWidget(btn_clear_log)
        h_log_btn.addStretch()
        self.lbl_log_stats = QLabel("INFO: 0  WARN: 0  ERROR: 0")
        self.lbl_log_stats.setStyleSheet("color:#4b5563;")
        h_log_btn.addWidget(self.lbl_log_stats)
        rv.addLayout(h_log_btn)

        splitter.addWidget(right)

        # 三栏比例（右栏加大到 460 以完整显示"实时日志"标题）
        splitter.setSizes([320, 540, 460])

        # ---- 底部状态栏 ----
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.lbl_status = QLabel("就绪")
        self.status_bar.addWidget(self.lbl_status, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(220)
        self.progress_bar.setTextVisible(True)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # 日志统计
        self._log_counts = {"INFO": 0, "WARN": 0, "ERROR": 0}

    def _connect(self):
        """连接信号"""
        self.bus.log.connect(self._on_log)
        self.bus.progress.connect(self._on_progress)

    # ---------------- 工具栏动作 ----------------
    def act_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片",
            "",
            "图片 (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;所有文件 (*.*)"
        )
        for f in files:
            self._add_file(f)
        self._refresh_summary()

    def act_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder:
            return
        exts = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")
        for root, _, files in os.walk(folder):
            for fn in files:
                if fn.lower().endswith(exts):
                    self._add_file(os.path.join(root, fn))
        self._refresh_summary()

    def act_clear(self):
        self.list_widget.clear()
        self.file_items.clear()
        self._refresh_summary()

    def act_choose_outdir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_dir)
        if d:
            self.output_dir = d
            self.act_outdir.setText(f"📤 输出目录: {d}")
            self.bus.log.emit("INFO", f"输出目录已更改为: {d}")

    def act_start(self):
        if self.worker and self.worker.isRunning():
            return
        if not self.file_items:
            QMessageBox.warning(self, "提示", "请先添加图片！")
            return
        os.makedirs(self.output_dir, exist_ok=True)
        params = self._collect_params()
        self.bus.log.emit("INFO", "─" * 60)
        self.bus.log.emit("INFO", f"开始批量处理 {len(self.file_items)} 张图片")
        self.bus.log.emit("INFO", f"输出目录: {self.output_dir}")
        self.bus.log.emit("INFO", f"参数: {asdict(params)}")

        # 设备选择（通过临时设置环境变量 + 切换缓存键）
        device_pref = self.cmb_device.currentData()
        if device_pref == "cpu":
            os.environ["BIREFNET_DEVICE"] = "cpu"
        else:
            os.environ.pop("BIREFNET_DEVICE", None)

        self.worker = ProcessWorker(
            items=list(self.file_items),
            dst_dir=self.output_dir,
            model_key=self.cmb_model.currentData(),
            params=params,
            input_size=self.sld_input_size.value(),
            log_bus=self.bus,
        )
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()
        self.act_start_action.setEnabled(False)
        self.lbl_status.setText("处理中...")

    def act_stop(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.bus.log.emit("WARN", "正在停止...")

    # ---------------- 输出尺寸预设 ----------------
    def _on_size_preset_changed(self, idx: int):
        """预设下拉变化时，更新画布宽高滑块"""
        if idx <= 0:
            return  # "自定义" 不改
        name, w, h, dpi, _tag = self.SIZE_PRESETS[idx]
        if w > 0 and h > 0:
            # 防止 valueChanged 递归触发 _on_canvas_changed
            self.sld_canvas_w.blockSignals(True)
            self.sld_canvas_h.blockSignals(True)
            self.sld_canvas_w.slider.setValue(w)
            self.sld_canvas_h.slider.setValue(h)
            self.sld_canvas_w.blockSignals(False)
            self.sld_canvas_h.blockSignals(False)
            self.bus.log.emit("INFO", f"输出尺寸预设: {name} ({w}×{h}px @ {dpi}ppi)")

    def _on_canvas_changed(self, _v: int):
        """用户手动改画布宽/高时，切换到'自定义'"""
        if self.cmb_size_preset.currentIndex() != 0:
            self.cmb_size_preset.blockSignals(True)
            self.cmb_size_preset.setCurrentIndex(0)
            self.cmb_size_preset.blockSignals(False)

    # ---------------- 文件列表 ----------------
    def _add_file(self, path: str):
        if path in self.file_items:
            return
        self.file_items.append(path)
        item = QListWidgetItem(self.list_widget)
        w = FileItemWidget(path)
        item.setSizeHint(QSize(0, 68))
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, w)
        # 引用：item -> widget
        self._item_widgets = getattr(self, "_item_widgets", {})
        self._item_widgets[path] = w

    def _refresh_summary(self):
        self.left_summary.setText(f"共 {len(self.file_items)} 张图片")

    # ---------------- 状态更新 ----------------
    def _on_log(self, level: str, text: str):
        # 颜色
        color = {
            "INFO": "#7ee787",
            "WARN": "#ffa657",
            "ERROR": "#ff7b72",
        }.get(level, "#c9d1d9")
        prefix = f'<span style="color:#8b949e;">[{time.strftime("%H:%M:%S")}]</span> ' \
                 f'<span style="color:{color}; font-weight:700;">{level}</span> '
        # 替换为 HTML
        from PySide6.QtCore import QTextStream
        self.txt_log.appendHtml(prefix + self._esc(text))
        self._log_counts[level] = self._log_counts.get(level, 0) + 1
        self.lbl_log_stats.setText(
            f"INFO: {self._log_counts['INFO']}  "
            f"WARN: {self._log_counts['WARN']}  "
            f"ERROR: {self._log_counts['ERROR']}"
        )

    def _on_progress(self, current: int, total: int, filename: str):
        if total > 0:
            pct = int(current * 100 / total)
            self.progress_bar.setValue(pct)
        # 更新文件项状态
        for path, w in getattr(self, "_item_widgets", {}).items():
            if os.path.basename(path) == filename:
                if current < total:
                    w.set_status("⏳ 处理中...", "#0369a1")
                else:
                    w.set_status("✓ 已完成", "#16a34a")
                break

    def _on_worker_finished(self):
        self.act_start_action.setEnabled(True)
        self.lbl_status.setText("已完成")
        self.progress_bar.setValue(100)

    # ---------------- 颜色选择 ----------------
    def _pick_text_color(self):
        c = QColorDialog.getColor(
            QColor(self.lbl_text_color.text()),
            self, "选择文字颜色",
            QColorDialog.ShowAlphaChannel
        )
        if c.isValid():
            self.lbl_text_color.setText(c.name())
            self.btn_text_color.setStyleSheet(
                f"background:{c.name()}; color:{'#fff' if c.lightness() < 128 else '#000'};"
                f" padding:4px 8px;"
            )

    # ---------------- 字体下拉框初始化 ----------------
    def _populate_font_combo(self):
        """扫描系统字体, 优先列出中文字体, 默认选中微软雅黑"""
        import platform
        self.cmb_text_font.clear()
        # 默认项 (留空 = worker.py 按 msyh→simhei→simsun 优先级自动选)
        self.cmb_text_font.addItem("系统默认 (优先微软雅黑)", "")
        # 通过 Qt 的 QFontDatabase 列出系统所有字体, 过滤出中文/拉丁常用
        families = QFontDatabase.families()
        priority_keywords = [
            "微软雅黑", "MSYH", "Microsoft YaHei", "YaHei",
            "黑体", "SimHei", "Heiti", "Hei",
            "宋体", "SimSun", "Songti",
            "华文细黑", "STXihei", "XIHEI",
            "苹方", "PingFang", "黑体-简", "冬青黑",
            "Noto Sans CJK", "Noto Serif CJK", "WenQuanYi", "Source Han",
            "Arial", "Segoe UI", "Times", "Calibri", "Verdana", "Tahoma",
        ]
        seen = set()
        # 优先级匹配项
        for kw in priority_keywords:
            for fam in families:
                if kw in fam and fam not in seen:
                    self.cmb_text_font.addItem(fam, fam)
                    seen.add(fam)
        # 补充其他所有字体 (用户可能想用特殊字体)
        for fam in families:
            if fam not in seen:
                self.cmb_text_font.addItem(fam, fam)
                seen.add(fam)
        # Windows 上默认选中"微软雅黑" (或近似匹配)
        if platform.system() == "Windows":
            for i in range(self.cmb_text_font.count()):
                txt = self.cmb_text_font.itemText(i)
                data = self.cmb_text_font.itemData(i)
                if data and ("微软雅黑" in txt or "YaHei" in txt or "MSYH" in txt):
                    self.cmb_text_font.setCurrentIndex(i)
                    break
        self.cmb_text_font.setToolTip(
            "默认优先微软雅黑。\n如需指定 .ttf/.ttc 文件, 可在代码 ProcessParams.font_path 设置完整路径"
        )

    # ---------------- 收集参数 ----------------
    def _collect_params(self) -> ProcessParams:
        p = ProcessParams()
        p.canvas_width = self.sld_canvas_w.value()
        p.canvas_height = self.sld_canvas_h.value()
        p.padding = self.sld_padding.value()
        p.center_subject = self.chk_center.isChecked()
        p.white_background = self.chk_whitebg.isChecked()
        p.add_text = self.chk_text.isChecked()
        p.text_size = self.sld_text_size.value()
        p.letter_spacing = self.sld_letter_spacing.value()
        p.text_color = self.lbl_text_color.text()
        p.text_position = "bottom" if "bottom" in self.cmb_text_pos.currentText() else "top"
        # 字体路径: 空字符串 = 让 worker.py 按优先级走系统默认 (微软雅黑优先)
        _fp = self.cmb_text_font.currentData()
        p.font_path = _fp if _fp else None
        # 文字带高度: 勾选"自动"则传 -1，否则使用滑块值
        p.text_band_height = -1 if self.chk_text_band_auto.isChecked() else int(self.sld_text_band.value())
        p.name_template = self.ed_template.text().strip()  # 空=使用原文件名
        fmt_text = self.cmb_format.currentText()
        if "PNG" in fmt_text:
            p.output_format = "PNG"
        elif "JPG" in fmt_text:
            p.output_format = "JPG"
        else:
            p.output_format = "JPEG"
        p.jpeg_quality = self.sld_quality.value()
        return p

    # ---------------- 辅助 ----------------
    def _esc(self, s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                 .replace(" ", "&nbsp;"))

    # ---------------- 参数持久化（QSettings） ----------------
    def _settings_keys(self):
        """集中管理所有需要持久化的参数名。增减参数时只改这里。
        命名规则: widget 属性名去掉 sld_/chk_/cmb_/ed_ 前缀后的剩余部分。"""
        return {
            "slider": [
                "input_size", "canvas_w", "canvas_h", "padding",
                "text_size", "letter_spacing", "text_band", "quality",
            ],
            "check": [
                "center", "whitebg",
                "text", "text_band_auto",
            ],
            "combo": [
                "text_pos", "text_font", "format", "model", "size_preset", "device",
            ],
            "text": ["template"],
            "label": ["text_color"],
            "path": ["output_dir"],
        }

    def _save_settings(self):
        """关闭时调用：保存所有 UI 参数到 QSettings"""
        s = QSettings()
        s.setValue("version", 1)
        keys = self._settings_keys()
        for k in keys["slider"]:
            w = getattr(self, f"sld_{k}", None)
            if w is not None:
                try:
                    s.setValue(f"slider/{k}", w.value())
                except Exception:
                    pass
        for k in keys["check"]:
            w = getattr(self, f"chk_{k}", None)
            if w is not None:
                s.setValue(f"check/{k}", w.isChecked())
        for k in keys["combo"]:
            w = getattr(self, f"cmb_{k}", None)
            if w is not None:
                s.setValue(f"combo/{k}/data", w.currentData() if w.currentData() is not None else w.currentText())
                s.setValue(f"combo/{k}/text", w.currentText())
        for k in keys["text"]:
            w = getattr(self, f"ed_{k}", None)
            if w is not None:
                s.setValue(f"text/{k}", w.text())
        for k in keys["label"]:
            w = getattr(self, f"lbl_{k}", None)
            if w is not None:
                s.setValue(f"label/{k}", w.text())
        for k in keys["path"]:
            v = getattr(self, k, None)
            if v:
                s.setValue(f"path/{k}", v)
        s.sync()

    def _load_settings(self):
        """启动时调用：从 QSettings 恢复所有 UI 参数。
        字段不存在/类型不匹配/超出范围时静默跳过，保持默认。
        期间临时 blockSignals，避免 cmb_size_preset 触发 _on_size_preset_changed
        覆盖已恢复的 sld_canvas_w/h。"""
        s = QSettings()
        if not s.contains("version"):
            return  # 首次启动，不加载
        keys = self._settings_keys()

        # 1. 先静音恢复所有控件（避免信号互覆盖）
        self.blockSignals(True)
        try:
            self._apply_settings_to_widgets(s, keys)
        finally:
            self.blockSignals(False)

        # 2. 主动触发 canvas/preset 的最终状态同步
        # 如果保存时是预设，则保留预设选中；如果是手工调过的 canvas，保留 canvas。
        # 由于 _on_size_preset_changed 在恢复时是静音的，这边手动按"预设 0"逻辑跳过
        idx_preset = self.cmb_size_preset.currentIndex()
        if idx_preset > 0 and idx_preset < len(self.SIZE_PRESETS):
            # 恢复时用户原选中的是某个预设：手动应用一次（signal 被解锁后会走到这里）
            self.cmb_size_preset.currentIndexChanged.emit(idx_preset)
        # 如果选中索引 0（"原图尺寸"），但 canvas w/h 不等于默认 1024/1024，
        # 说明用户是手工调过的，保持当前 canvas 即可。

    def _apply_settings_to_widgets(self, s: QSettings, keys: dict):
        """_load_settings 的实际恢复逻辑，外部调用需 blockSignals 包裹。"""
        for k in keys["slider"]:
            if not s.contains(f"slider/{k}"):
                continue
            w = getattr(self, f"sld_{k}", None)
            if w is None:
                continue
            try:
                v = int(s.value(f"slider/{k}"))
                # LabeledSlider 内部有 .slider (QSlider)，其上才有 minimum/maximum
                _sl = getattr(w, "slider", None)
                if _sl is not None:
                    mn, mx = _sl.minimum(), _sl.maximum()
                else:
                    mn, mx = w.minimum(), w.maximum()
                if mn <= v <= mx:
                    w.setValue(v)
            except Exception:
                pass
        for k in keys["check"]:
            if not s.contains(f"check/{k}"):
                continue
            w = getattr(self, f"chk_{k}", None)
            if w is None:
                continue
            try:
                w.setChecked(str(s.value(f"check/{k}")).lower() in ("true", "1", "yes"))
            except Exception:
                pass
        for k in keys["combo"]:
            w = getattr(self, f"cmb_{k}", None)
            if w is None:
                continue
            # 优先按 data 匹配（避免文本变化导致不匹配），备选按 text
            data_v = s.value(f"combo/{k}/data")
            if data_v is not None:
                idx = w.findData(data_v)
                if idx >= 0:
                    w.setCurrentIndex(idx)
                    continue
            text_v = s.value(f"combo/{k}/text")
            if text_v is not None:
                idx = w.findText(str(text_v))
                if idx >= 0:
                    w.setCurrentIndex(idx)
        for k in keys["text"]:
            if not s.contains(f"text/{k}"):
                continue
            w = getattr(self, f"ed_{k}", None)
            if w is None:
                continue
            try:
                w.setText(str(s.value(f"text/{k}")))
            except Exception:
                pass
        for k in keys["label"]:
            if not s.contains(f"label/{k}"):
                continue
            w = getattr(self, f"lbl_{k}", None)
            if w is None:
                continue
            try:
                v = str(s.value(f"label/{k}"))
                if v.startswith("#") and len(v) in (4, 7, 9):  # 简单校验
                    w.setText(v)
            except Exception:
                pass
        for k in keys["path"]:
            if not s.contains(f"path/{k}"):
                continue
            v = str(s.value(f"path/{k}"))
            if v and os.path.isdir(v):
                setattr(self, k, v)
                # 同步更新工具栏显示
                if k == "output_dir":
                    self.act_outdir.setText(f"📤 输出目录: {v}")

    def closeEvent(self, ev):
        """窗口关闭时保存参数。QThread 已在 _on_worker_finished 中等待。"""
        try:
            self._save_settings()
        except Exception:
            pass
        super().closeEvent(ev)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("WhiteStudio")
    app.setOrganizationName("WhiteStudio")
    app.setStyle("Fusion")

    # 浅色 Fusion 调色
    app.setStyleSheet("""
        QMainWindow, QWidget { background:#f8fafc; color:#1f2937; }
        QToolBar { background:#ffffff; border-bottom:1px solid #e5e7eb; padding:4px; }
        QToolBar QToolButton { padding:6px 12px; border-radius:4px; }
        QToolBar QToolButton:hover { background:#f1f5f9; }
        QGroupBox {
            background:#ffffff;
            border:1px solid #e5e7eb;
            border-radius:6px;
            margin-top:14px;
            padding:12px;
            font-weight:600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding:0 6px;
            color:#1f2937;
        }
        QPushButton {
            background:#ffffff;
            border:1px solid #d1d5db;
            padding:4px 10px;
            border-radius:4px;
        }
        QPushButton:hover { background:#f9fafb; }
        QPushButton:pressed { background:#f3f4f6; }
        QSlider::groove:horizontal {
            background:#e5e7eb; height:6px; border-radius:3px;
        }
        QSlider::sub-page:horizontal {
            background:#3b82f6; border-radius:3px;
        }
        QSlider::handle:horizontal {
            background:#ffffff; border:2px solid #3b82f6;
            width:18px; height:18px; margin:-6px 0; border-radius:9px;
        }
        QListWidget { background:#ffffff; }
        QSplitter::handle { background:#e5e7eb; }
        QStatusBar { background:#ffffff; border-top:1px solid #e5e7eb; }
    """)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
