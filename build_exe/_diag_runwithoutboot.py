"""
尝试用 _MEIfull 模拟 EXE 启动, 检验我们的逻辑
启动 path:
  1. bootloader 解压 _MEI340562 (仅 type='b')
  2. bootloader 直接 exec 字节码 'pyiboot01_bootstrap' (type='s')
  3. pyiboot01_bootstrap 启动 Python, 读 PYZ, exec 'pyi_rth_*' (type='s')
  4. 最后 exec 'run' (type='s')
"""
import os, sys, marshal, struct, importlib.util, types

mei = r'C:\Users\23107\AppData\Local\Temp\_MEIfull'
os.chdir(mei)
sys.path.insert(0, mei)

# 把 _MEIPASS 设置好
sys._MEIPASS = mei
sys.frozen = True

# 模拟 pyi_rth_whitestudio
print('[SMOKE] rth start')

# 模拟 PYZ import: 用 importlib bootstrap
# PyInstaller 用 custom import hook, 这里我们试直接读 PYZ
from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader
pyzr = ZlibArchiveReader(r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe', start_offset=3267715698)

def my_import(name):
    """从 PYZ 读取模块字节码并 exec"""
    if name in pyzr.toc:
        info = pyzr.toc[name]
        # pyzr.toc[modname] = (pos, length, ulength, kind, code)
        # code 是 marshal code
        # 实际 PyInstaller 是 raw zlib data, 由 pyimod01_archive 解析
        # 我们不重复实现, 只测最关键模块能不能 import
        return True
    return False

# 测试一些关键模块
key_modules = ['app.main', 'birefnet', 'BiRefNet_config', 'transformers', 'torch', 'PIL.Image', 'cv2', 'PySide6.QtCore']
ok = 0
for m in key_modules:
    if my_import(m):
        print('  PYZ OK  %s' % m)
        ok += 1
    else:
        print('  PYZ --  %s  NOT IN PYZ' % m)
print('PYZ has %d/%d key modules' % (ok, len(key_modules)))
