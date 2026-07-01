"""
模拟 PyInstaller bootloader 的解压流程, 看 PYZ 能否被正确解压到 _MEI 目录
"""
import os, sys, tempfile, shutil
from PyInstaller.archive.readers import CArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'

# 清空 _MEI
for d in os.listdir(os.environ['TEMP']):
    if d.startswith('_MEI'):
        full = os.path.join(os.environ['TEMP'], d)
        if os.path.isdir(full):
            try: shutil.rmtree(full, ignore_errors=True)
            except: pass
print('Cleared _MEI* directories')

# 打开 CArchive
reader = CArchiveReader(src)
toc = reader.toc
print(f'Total entries: {len(toc)}')

# 准备 _MEI 目录
mei_dir = os.path.join(os.environ['TEMP'], '_MEItest')
if os.path.exists(mei_dir): shutil.rmtree(mei_dir)
os.makedirs(mei_dir)
print(f'Created {mei_dir}')

# 遍历所有 entry 解压到 _MEI
ok, fail, pyz_ok = 0, 0, False
for name, (off, length, uslength, cflag, typcd) in toc.items():
    target = os.path.join(mei_dir, name.replace('/', os.sep))
    if name.endswith('/') or name.endswith('\\'):
        os.makedirs(target, exist_ok=True)
        ok += 1
        continue
    os.makedirs(os.path.dirname(target), exist_ok=True)
    try:
        data = reader.extract(name)
        with open(target, 'wb') as f:
            f.write(data)
        ok += 1
        if name == 'PYZ-00.pyz':
            pyz_ok = True
            print(f'  PYZ extracted: {len(data):,} bytes to {target}')
    except Exception as e:
        fail += 1
        print(f'  FAIL {name}: {e}')

print(f'\nExtracted: ok={ok}  fail={fail}  pyz_ok={pyz_ok}')
print(f'_MEItest PYZ-00.pyz exists: {os.path.exists(os.path.join(mei_dir, "PYZ-00.pyz"))}')
if os.path.exists(os.path.join(mei_dir, "PYZ-00.pyz")):
    print(f'  size: {os.path.getsize(os.path.join(mei_dir, "PYZ-00.pyz")):,} bytes')

# 关键: 模拟 bootloader 下一步 - 启动子进程
# bootloader 实际上 execvp _MEI\python312.dll via runw _MEI\python.exe (which is part of bootloader itself)
# 但 _MEI 里没有 python.exe/WhiteStudio.exe
# bootloader 是把 .exe 自己 + child process 加载 _MEI 后, 用自己的 image 再次 execvp
# 也就是说, _MEI 不需要 python.exe! bootloader 的子进程就是 WhiteStudio.exe 自己 (重命名后)
# bootloader 重命名为 pyi-windows-... 然后用 _MEI 路径作为 -p pythonpath 启动

# 关键问题: 子进程需要 `python` 命令启动 PYZ 字节码
# 看 PyInstaller 源码, bootloader 启动子进程时:
# 1. 把 _MEI 加到 PYTHONPATH
# 2. exec `_MEI\python.exe` (PYZ 解压后)  不对, PYZ 不是 python.exe
# 实际上 PYZ-00.pyz 是被 python 通过 path_hooks 加载, 不需要直接 exec

# 真正流程: bootloader 调用 CreateProcessW 启动自己 (WhiteStudio.exe) 作为子进程,
#   子进程的命令行包含 _MEI 路径, 子进程 exec 时把 _MEI 加 PYTHONPATH,
#   启动 python 解释器 (内置的), python 启动时 import struct (来自 PYZ)
print('\n--- 看 PyInstaller 6 源码: bootloader 怎么启动子进程 ---')
import PyInstaller
pyinst_dir = os.path.dirname(PyInstaller.__file__)
print(f'PyInstaller dir: {pyinst_dir}')
for f in os.listdir(os.path.join(pyinst_dir, 'bootloader', 'Windows-64bit-intel')):
    print(f'  bootloader: {f}')

# 找 launch.c
launcher = os.path.join(pyinst_dir, 'bootloader', 'common', 'launch.c')
if os.path.exists(launcher):
    print(f'\nlaunch.c exists, size={os.path.getsize(launcher)} bytes')
