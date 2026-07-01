"""
完整 type 分布
"""
import os
from PyInstaller.archive.readers import CArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
reader = CArchiveReader(src)
toc = reader.toc

# type 分布
from collections import Counter
types = Counter(e[4] for n, e in toc.items())
print(f'Type distribution: {dict(types)}')

# 找 'x' (DATA) 的前 10
x_entries = [(n, e) for n, e in toc.items() if e[4] == 'x']
print(f'\\nDATA (x) entries: {len(x_entries)}')
print('First 20:')
for n, e in x_entries[:20]:
    print(f'  {n!r}  size={e[2]:,}  comp={e[3]}')

# 找 'b' (BINARY)
b_entries = [(n, e) for n, e in toc.items() if e[4] == 'b']
print(f'\\nBINARY (b) entries: {len(b_entries)}')

# 关键: type='s' 7 个, type='m' 5 个 - 都是 bootloader/import hooks 必需的
print(f'\\nAll 7 type="s" entries:')
for n, e in [(n, e) for n, e in toc.items() if e[4] == 's']:
    print(f'  {n!r}  off={e[0]:,}  len={e[1]:,}')

print(f'\\nAll 5 type="m" entries:')
for n, e in [(n, e) for n, e in toc.items() if e[4] == 'm']:
    print(f'  {n!r}  off={e[0]:,}  len={e[1]:,}')
