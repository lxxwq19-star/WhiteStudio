"""
直接 python run.py 启动, 但把 sys._MEIPASS 指向 _MEIfull, 把 PYZ import 链路设置好
模拟 EXE 启动流程
"""
import os, sys

mei = r'C:\Users\23107\AppData\Local\Temp\_MEIfull'
os.chdir(mei)
sys.path.insert(0, mei)

# 模拟 frozen 状态
sys._MEIPASS = mei
sys.frozen = True

# 替换 import 系统: PYZ 的 import hook
# PyInstaller 6 的 pyimod02_importers 会做这个, 但它需要 pyimod01_archive 才能正常工作
# 我们直接用 PyInstaller 自带的 PyInstaller/loader
import importlib
import importlib.util
import importlib.machinery
import _imp

# 简化: 不替换 import 钩子, 改成手动 import 关键模块
# 1. 我们的 rth: import torch
print('[1] torch import...', flush=True)
import torch
print(f'    OK torch {torch.__version__}', flush=True)

# 2. 看 PySide6 能不能 import
print('[2] PySide6 import...', flush=True)
try:
    from PySide6 import QtCore, QtWidgets
    print(f'    OK PySide6', flush=True)
except Exception as e:
    print(f'    FAIL: {e}', flush=True)

# 3. 看 birefnet_local 路径下的 birefnet 能不能 import
print('[3] birefnet_local/birefnet import...', flush=True)
sys.path.insert(0, os.path.join(mei, 'birefnet_local'))
try:
    import birefnet
    print(f'    OK birefnet {birefnet}', flush=True)
except Exception as e:
    print(f'    FAIL: {e!r}', flush=True)

# 4. 关键: app/main
print('[4] app.main import...', flush=True)
try:
    import app.main
    print(f'    OK app.main', flush=True)
except Exception as e:
    print(f'    FAIL: {e!r}', flush=True)
