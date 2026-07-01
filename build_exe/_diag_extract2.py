"""
完整用 PyInstaller CArchiveReader 提取所有 entry 到 _MEI
"""
import os, shutil
from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
reader = CArchiveReader(src)
toc = reader.toc
print(f'TOC entries: {len(toc)}')

mei_dir = r'C:\Users\23107\AppData\Local\Temp\_MEImanual'
if os.path.exists(mei_dir): shutil.rmtree(mei_dir, ignore_errors=True)
os.makedirs(mei_dir)

# 提取 PYZ.pyz
pyz_data = reader.extract('PYZ.pyz')
print(f'PYZ data extracted: {len(pyz_data):,} bytes ({len(pyz_data)/1e6:.1f}MB)')
pyz_path = os.path.join(mei_dir, 'PYZ.pyz')
with open(pyz_path, 'wb') as f:
    f.write(pyz_data)
print(f'Saved: {pyz_path}')
print(f'  file size: {os.path.getsize(pyz_path):,} bytes')

# 解析 PYZ
pyzr = ZlibArchiveReader(pyz_path)
print(f'\\nPYZ opened, modules: {len(pyzr.toc)}')
print(f'  First 5:')
for n, e in list(pyzr.toc.items())[:5]:
    print(f'    {n!r}  {e}')

# 提取 'run' (主入口)
print(f'\\n=== Try to extract main entry "run" ===')
try:
    run_data = reader.extract('run')
    print(f'  run data: {len(run_data)} bytes')
    run_path = os.path.join(mei_dir, 'run.pyc')
    with open(run_path, 'wb') as f:
        f.write(run_data)
    print(f'  saved: {run_path}')
except Exception as e:
    print(f'  FAIL: {e}')

# 提取 'struct' (Python struct module)
print(f'\\n=== Try to extract "struct" ===')
try:
    struct_data = reader.extract('struct')
    print(f'  struct data: {len(struct_data)} bytes')
except Exception as e:
    print(f'  FAIL: {e}')
