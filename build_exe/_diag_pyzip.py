"""
模拟 bootloader: 用 PyInstaller.archive.readers 提取 PYZ-00.pyz
"""
import os, shutil
from PyInstaller.archive.readers import CArchiveReader, PYZReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
reader = CArchiveReader(src)
toc = reader.toc

# 看 PYZ entry
pyz_entry = toc['PYZ-00.pyz']
print(f'PYZ entry: {pyz_entry}')

# 尝试用 PYZReader 直接打开
# PYZ entry 在 CArchive 中的 data_offset 是 PYZ CArchive 在 EXE 内的偏移
# 46954106 = 44.8MB PYZ 大小
pyz_off = pyz_entry[0]
pyz_len = pyz_entry[1]
print(f'PYZ data: offset={pyz_off:,}, length={pyz_len:,}')

# 提取 PYZ 数据到临时文件
mei_dir = r'C:\Users\23107\AppData\Local\Temp\_MEIdiag'
if os.path.exists(mei_dir): shutil.rmtree(mei_dir, ignore_errors=True)
os.makedirs(mei_dir)

# 1) 从 CArchive 提取 PYZ
pyz_data = reader.extract('PYZ-00.pyz')
print(f'CArchive extract PYZ size: {len(pyz_data):,}')
pyz_path = os.path.join(mei_dir, 'PYZ-00.pyz')
with open(pyz_path, 'wb') as f:
    f.write(pyz_data)
print(f'Saved PYZ to {pyz_path} ({os.path.getsize(pyz_path):,} bytes)')

# 2) 用 PYZReader 解析
pyzr = PYZReader(pyz_path)
print(f'PYZReader opened: {pyzr}')

# 列出 PYZ 内所有模块
mods = list(pyzr.toc.keys())
print(f'PYZ modules count: {len(mods)}')
print(f'First 10: {mods[:10]}')

# 关键: 如果 PYZ 解析成功, 说明 EXE 内 PYZ 是健康的
