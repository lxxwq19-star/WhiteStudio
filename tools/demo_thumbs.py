"""
模拟 GUI 添加 3 张测试图，截屏看缩略图是否加载
"""
import os
import sys
import time

os.chdir(r"C:\Users\23107\.qclaw\workspace\birefnet_whitestudio")
sys.path.insert(0, ".")

# 创建 3 张测试图
from PIL import Image
os.makedirs("test_output", exist_ok=True)

samples = [
    ("demo_a.png", (300, 200), (220, 100, 50)),
    ("demo_b.png", (400, 300), (50, 200, 100)),
    ("demo_c.png", (250, 250), (200, 50, 200)),
]
for name, size, color in samples:
    im = Image.new("RGB", size, color)
    # 画一个简单形状
    for x in range(20, size[0]-20, 30):
        for y in range(20, size[1]-20, 30):
            im.putpixel((x, y), (255, 255, 255))
    im.save(f"test_output/{name}")
    print(f"Created test_output/{name} ({size[0]}x{size[1]})")

# 通过 GUI 自动化或直接给 QListWidget 添加
# 用 PyAutoGUI 不靠谱（窗口可能被 QClaw 遮挡），直接用 Qt 测试
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QEventLoop
from app.main import FileItemWidget, MainWindow

app = QApplication.instance() or QApplication(sys.argv)

# 直接 new MainWindow
w = MainWindow()
w.show()
# 等 1 秒初始化
loop = QEventLoop()
QTimer.singleShot(1500, loop.quit)
loop.exec()

# 添加 3 张图
for name, _, _ in samples:
    w._add_file(f"C:\\Users\\23107\\.qclaw\\workspace\\birefnet_whitestudio\\test_output\\{name}")
w._refresh_summary()

# 等缩略图加载 (子线程 + 临时文件 + 主线程 QImage 加载)
loop = QEventLoop()
QTimer.singleShot(4000, loop.quit)
loop.exec()

# 检查缩略图是否出现
items_with_no_thumb = 0
for i in range(w.list_widget.count()):
    item = w.list_widget.item(i)
    widget = w.list_widget.itemWidget(item)
    pix = widget.thumb.pixmap()
    if pix is None or pix.isNull():
        items_with_no_thumb += 1
        print(f"  [{i}] {os.path.basename(widget.path)}: 缩略图 MISS")
    else:
        print(f"  [{i}] {os.path.basename(widget.path)}: 缩略图 {pix.width()}x{pix.height()}")

print(f"\n未加载缩略图: {items_with_no_thumb}/{w.list_widget.count()}")
print(f"列表总条目: {w.list_widget.count()}, 文件数: {len(w.file_items)}")

# 让窗口留在主屏可见位置 — 只 MoveWindow，不 SetForegroundWindow (避免前台锁)
import ctypes
hwnd = int(w.winId())
ctypes.windll.user32.MoveWindow(hwnd, 60, 60, 1760, 1160, True)
# 注意：故意不调用 SetForegroundWindow — 截图工具用离屏位图抓取

# 等 Qt 完成绘制
loop = QEventLoop()
QTimer.singleShot(2000, loop.quit)
loop.exec()
print("Window moved to (60,60,1760,1160), ready for screenshot")

# **关键**：让窗口持续驻留，外部脚本可以反复截图
# 用一个永远不触发的定时器保持事件循环
_keeper = QTimer()
_keeper.setInterval(3600_000)  # 1 小时
_keeper.start()
_keep_alive = {"done": False}

def _on_kill():
    _keep_alive["done"] = True
    app.quit()

# 监听 SIGINT/SIGTERM 优雅退出
import signal
signal.signal(signal.SIGINT, lambda *_: _on_kill())
signal.signal(signal.SIGTERM, lambda *_: _on_kill())

print(f"PID={os.getpid()} | Window will stay alive. Send Ctrl+C / taskkill to exit.")
print("DEMO_READY")  # 外部脚本看到这个 token 后可以截图
sys.stdout.flush()

# 进入主事件循环（不会自己退出）
sys.exit(app.exec())
