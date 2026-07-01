"""
直接 import 一些 PYZ 模块验证 PYZ 完整
"""
from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
reader = CArchiveReader(src)
pyz_start_in_exe = 3267715698
pyzr = ZlibArchiveReader(src, start_offset=pyz_start_in_exe)

key_modules = [
    'PIL.Image',
    'transformers',
    'torch',
    'numpy',
    'cv2',
    'PySide6.QtCore',
    'app.main',
    'birefnet',
    'BiRefNet_config',
    'timm.models',
    'einops',
    'safetensors.torch',
    'app.worker',
]
print('PYZ modules total: %d' % len(pyzr.toc))
for m in key_modules:
    if m in pyzr.toc:
        info = pyzr.toc[m]
        print('  OK  %-40s  pos=%d' % (m, info[0]))
    else:
        print('  --  %-40s  MISSING' % m)
