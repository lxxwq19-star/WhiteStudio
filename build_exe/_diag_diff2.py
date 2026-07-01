"""
对比 _MEI340562 vs _MEIfull 顶层文件
"""
import os
mei = r'C:\Users\23107\AppData\Local\Temp\_MEI340562'
full = r'C:\Users\23107\AppData\Local\Temp\_MEIfull'

a = set(os.listdir(mei))
b = set(os.listdir(full))
print(f'_MEI340562 top: {len(a)}')
print(f'_MEIfull  top: {len(b)}')
print(f'In _MEIfull but NOT in _MEI340562: {len(b - a)}')
for n in sorted(b - a):
    full_p = os.path.join(full, n)
    if os.path.isfile(full_p):
        print(f'  {n}  size={os.path.getsize(full_p):,}')
    else:
        print(f'  [DIR] {n}')
print(f'\nIn _MEI340562 but NOT in _MEIfull: {len(a - b)}')
for n in sorted(a - b):
    p = os.path.join(mei, n)
    if os.path.isfile(p):
        print(f'  {n}  size={os.path.getsize(p):,}')
    else:
        print(f'  [DIR] {n}')
