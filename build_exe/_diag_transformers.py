"""
精确对比: app/main.py 是 TOC entry 'app/main' 还是目录 'app/' ?
"""
import os
from PyInstaller.archive.readers import CArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
reader = CArchiveReader(src)
toc = reader.toc

# 找 app 相关的所有 entry
app_entries = [(n, toc[n]) for n in toc if n.startswith('app/') or n == 'app']
print(f'App-related entries: {len(app_entries)}')
for n, e in app_entries[:30]:
    print(f'  {n!r}  type={e[4]}')
print(f'...')

# 找 transformers 顶层
trans_entries = [(n, toc[n]) for n in toc if n.startswith('transformers/') and n.count('/') <= 2][:30]
print(f'\\nTransformers top-level entries (first 30):')
for n, e in trans_entries:
    print(f'  {n!r}  type={e[4]}')

# 关键: 'struct' 是 module, 看下 type 和 size
struct_entry = toc.get('struct')
print(f'\\n"struct" entry: {struct_entry}')

# 找所有 type='s' 和 type='m'
s_entries = [(n, e) for n, e in toc.items() if e[4] == 's']
m_entries = [(n, e) for n, e in toc.items() if e[4] == 'm']
M_entries = [(n, e) for n, e in toc.items() if e[4] == 'M']
z_entries = [(n, e) for n, e in toc.items() if e[4] == 'z']
print(f'\\nType counts: s={len(s_entries)}  m={len(m_entries)}  M={len(M_entries)}  z={len(z_entries)}')
