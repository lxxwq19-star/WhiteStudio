"""
清理 main.py: 移除 DIAG 块, 保留绝对 import + sys.path 修复
"""
import shutil, re

p = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\app\main.py'
text = open(p, 'r', encoding='utf-8').read()

# 删除 DIAG 块
text = re.sub(
    r'\n*import os as _diag_os\ntry:.*?except Exception:\n    pass\n+',
    '\n',
    text,
    flags=re.DOTALL,
)
# 也删除可能残留
text = text.replace(
    'import os as _diag_os\ntry:\n    with open(r\'C:\\Users\\23107\\ws_main_marker.log\', \'a\', encoding=\'utf-8\') as _df:\n        _df.write(f\'[MAIN_ENTER] pid={_diag_os.getpid()}\\n\')\nexcept Exception:\n    pass\n\n',
    '',
)

# 删除绝对 import 前的 hack (旧 diag 替换 _appdir_here 那段)
# 注意: 我们**要保留** _appdir_here 那段 (它修复 from . import worker 失败)
# 但去掉 diag 那一行
# 找 _appdir_here 块
idx = text.find('import os as _appdir')
print('Found _appdir at', idx)

open(p, 'w', encoding='utf-8').write(text)
print('Cleaned, size:', len(text))

# 验证
for m in re.finditer(r'^(import|from)\s+[\w.]*\s*.*$', text, re.MULTILINE):
    print('IMPORT:', m.group(0))
