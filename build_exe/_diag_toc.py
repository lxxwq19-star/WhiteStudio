import os
from PyInstaller.archive.readers import CArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
reader = CArchiveReader(src)
toc = reader.toc
print(f'TOC entries: {len(toc)}')
print(f'\\nAll PYZ-related keys:')
for k in toc:
    if 'PYZ' in str(k) or 'pyz' in str(k):
        print(f'  {k!r}  type={type(k).__name__}')

# 查 'PYZ-00.pyz' 是哪个 key
print(f'\\n"PYZ-00.pyz" in toc: {"PYZ-00.pyz" in toc}')
print(f'b"PYZ-00.pyz" in toc: {b"PYZ-00.pyz" in toc}')

# 打印前 10 个 keys
print(f'\\nFirst 10 keys (raw):')
for i, k in enumerate(list(toc.keys())[:10]):
    print(f'  [{i}] {k!r} type={type(k).__name__}')

# 找 包含 PYZ 的 keys
all_keys = list(toc.keys())
pyz_keys = [k for k in all_keys if 'PYZ' in str(k) or 'pyz' in str(k)]
print(f'\\nTotal PYZ keys: {len(pyz_keys)}')
for k in pyz_keys[:5]:
    print(f'  {k!r}')
