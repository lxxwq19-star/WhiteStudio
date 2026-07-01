"""
模拟 bootloader: 找 PYZ 提取的正确 API
"""
import os, shutil, importlib
import PyInstaller.archive.readers as r
print('readers module:', r.__file__)
print('available classes:', [x for x in dir(r) if 'Reader' in x or 'CArchive' in x or 'PYZ' in x])

# 试试 submodule
try:
    import PyInstaller.archive.pyz as pyz_mod
    print(f'\\npyz module: {pyz_mod.__file__}')
    print(f'  available: {[x for x in dir(pyz_mod) if not x.startswith("_")]}')
except ImportError as e:
    print(f'pyz module import: {e}')

# 试 PYZ archive
try:
    import PyInstaller.archive
    print(f'\\nPyInstaller.archive available: {[x for x in dir(PyInstaller.archive) if not x.startswith("_")]}')
except Exception as e:
    print(f'archive: {e}')
