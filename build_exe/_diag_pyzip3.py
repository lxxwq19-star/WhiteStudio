"""
完整模拟 bootloader: 用 ZlibArchiveReader 解析 PYZ-00.pyz
"""
import os, shutil
from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
reader = CArchiveReader(src)
toc = reader.toc

mei_dir = r'C:\Users\23107\AppData\Local\Temp\_MEIdiag2'
if os.path.exists(mei_dir): shutil.rmtree(mei_dir, ignore_errors=True)
os.makedirs(mei_dir)

# 1) 从 CArchive 提取 PYZ
print('=== Step 1: Extract PYZ from CArchive ===')
pyz_data = reader.extract('PYZ-00.pyz')
print(f'PYZ size: {len(pyz_data):,} bytes')
pyz_path = os.path.join(mei_dir, 'PYZ-00.pyz')
with open(pyz_path, 'wb') as f:
    f.write(pyz_data)

# 2) ZlibArchiveReader 解析 PYZ
print('\\n=== Step 2: ZlibArchiveReader ===')
pyzr = ZlibArchiveReader(pyz_path)
print(f'PYZReader: {pyzr}')
print(f'PYZ toc size: {len(pyzr.toc)}')
print(f'First 5 entries:')
for i, (name, entry) in enumerate(pyzr.toc.items()):
    if i >= 5: break
    print(f'  {name!r}  {entry[:4]}')

# 3) 提取 main 脚本字节码
print('\\n=== Step 3: Try to extract main module ===')
# 找 __main__ 或 run
for name in list(pyzr.toc.keys())[:50]:
    if 'main' in name.lower() or name in ('run', 'app'):
        print(f'  candidate: {name!r}')

# 试直接读 __main__
try:
    data = pyzr.extract('__main__')
    print(f'\\n__main__ extracted: {len(data)} bytes')
except Exception as e:
    print(f'\\n__main__ not in PYZ: {e}')

# 试 run
try:
    data = pyzr.extract('run')
    print(f'\\nrun extracted: {len(data)} bytes')
except Exception as e:
    print(f'\\nrun not in PYZ: {e}')
