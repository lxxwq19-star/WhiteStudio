"""
把 DIAG 移到 main.py 顶部 (docstring 之前)
"""
import shutil, os

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\app\main.py'
text = open(src, 'r', encoding='utf-8').read()

# 删除现有 DIAG
marker_str = "import os as _diag_os"
idx = text.find(marker_str)
if idx > 0:
    # 向前找 \n\n 之前
    prev_double = text.rfind('\n\n', 0, idx)
    # 向后找 \n\n 之后
    next_double = text.find('\n\n', idx)
    if prev_double >= 0 and next_double > 0:
        text = text[:prev_double] + text[next_double:]
        print(f'[1] Removed existing DIAG block')

# 找 docstring 开始 ""\"\n
doc_start = text.find('"""\n')
if doc_start != 0:
    # docstring 不在第一行 — 找首个 \n
    print('[!] docstring not at start, refactoring')
    # 找第一个 """
    doc_start = text.find('"""')

diag = (
    "import os as _diag_os\n"
    "try:\n"
    "    with open(r'C:\\Users\\23107\\ws_main_marker.log', 'a', encoding='utf-8') as _df:\n"
    "        _df.write(f'[MAIN_ENTER] pid={_diag_os.getpid()}\\n')\n"
    "except Exception:\n"
    "    pass\n\n"
)

new_text = diag + text
open(src, 'w', encoding='utf-8').write(new_text)
print(f'[2] DIAG prepended, size {len(new_text)}')

# 同步到 _MEIfull
mei_main = r'C:\Users\23107\AppData\Local\Temp\_MEIfull\app\main.py'
shutil.copy(src, mei_main)
print(f'[3] Copied to _MEIfull')

# 验证
v = open(mei_main, 'r', encoding='utf-8').read()
print(f'[4] First 300:')
print(v[:300])
print(f'...[5] from __future__ pos: {v.find("from __future__")}')
print(f'...[6] docstring start pos: {v.find(chr(34)+chr(34)+chr(34))}')
