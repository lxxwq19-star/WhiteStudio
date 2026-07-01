import os
p = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\app\main.py'
text = open(p, 'r', encoding='utf-8').read()
print('size:', len(text))
print('contains from . import worker:', 'from . import worker' in text)
print('contains import worker:', 'import worker' in text)
print('contains _appdir:', '_appdir' in text)
print('contains _diag:', '_diag' in text)
# 找所有 import worker 块
import re
for m in re.finditer(r'^(import|from)\s+[\w.]*\s*.*$', text, re.MULTILINE):
    print('IMPORT:', m.group(0))
