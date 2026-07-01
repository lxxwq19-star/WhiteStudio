"""
对比 CArchiveReader.toc 4820 entries vs _MEI 4807 files
"""
import os
from PyInstaller.archive.readers import CArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
reader = CArchiveReader(src)
toc = reader.toc
print(f'TOC entries: {len(toc)}')

# _MEI 实际文件
mei = r'C:\Users\23107\AppData\Local\Temp\_MEI340562'
mei_files = set()
for root, dirs, files in os.walk(mei):
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, mei)
        mei_files.add(rel.replace('\\', '/'))

print(f'_MEI files: {len(mei_files)}')

# 找 toc 中不在 _MEI 的
toc_names = set(toc.keys())
print(f'TOC names: {len(toc_names)}')
print(f'Diff: TOC - _MEI:')
missing = []
for n in toc_names:
    n_norm = n.replace('\\', '/')
    if n_norm not in mei_files:
        missing.append(n)
for m in missing[:30]:
    print(f'  {m!r}  type={toc[m][4]}')
print(f'... total missing: {len(missing)}')
