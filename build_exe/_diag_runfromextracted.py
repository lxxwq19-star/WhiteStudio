"""
完整提取 EXE 内所有 entry 到 _MEI
"""
import os, shutil
from PyInstaller.archive.readers import CArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
print(f'Reading: {src}')
reader = CArchiveReader(src)
toc = reader.toc
print(f'TOC: {len(toc)} entries')

# 准备 _MEI 目录
mei_dir = r'C:\Users\23107\AppData\Local\Temp\_MEIfull'
if os.path.exists(mei_dir): shutil.rmtree(mei_dir, ignore_errors=True)
os.makedirs(mei_dir)
print(f'Created: {mei_dir}')

# 提取所有 entry
extracted = 0
for name, (off, length, ulength, comp, typ) in toc.items():
    target = os.path.join(mei_dir, name)
    parent = os.path.dirname(target)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    try:
        data = reader.extract(name)
        with open(target, 'wb') as f:
            f.write(data)
        extracted += 1
    except Exception as e:
        print(f'FAIL {name} (typ={typ}): {e}')

print(f'\nExtracted: {extracted} / {len(toc)} entries')

# 列出 _MEI 顶层
top = sorted(os.listdir(mei_dir))
print(f'\n_MEI 顶层 ({len(top)} entries), 找关键文件:')
for k in ['PYZ-00.pyz', 'PYZ.pyz', 'run', 'struct', 'pyimod01_archive', 'pyiboot01_bootstrap', 'pyi_rth_whitestudio']:
    p = os.path.join(mei_dir, k)
    if os.path.exists(p):
        print(f'  ✓ {k}  size={os.path.getsize(p):,}')
    else:
        print(f'  ✗ {k}  MISSING')
