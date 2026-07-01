"""
正确顺序: docstring -> from __future__ -> DIAG -> other imports
"""
import shutil

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\app\main.py'
text = open(src, 'r', encoding='utf-8').read()

# 删除所有现有 DIAG 块
import re
text = re.sub(
    r'\n*import os as _diag_os\ntry:.*?pass\n',
    '\n\n',
    text,
    flags=re.DOTALL,
)
text = re.sub(
    r'^import os as _diag_os\ntry:.*?pass\n+',
    '',
    text,
    flags=re.DOTALL | re.MULTILINE,
)

# 检查 from __future__ 位置
ff_pos = text.find('from __future__ import annotations')
if ff_pos == -1:
    print('[!] from __future__ not found!')
else:
    # 在 from __future__ 行后, 空行后, 插入 DIAG
    insert_at = ff_pos
    newline = text.find('\n', insert_at)
    newline2 = text.find('\n', newline+1)
    # 在 from __future__ 后的空行后插
    insert_at = newline2 + 1
    
    diag = (
        "import os as _diag_os\n"
        "try:\n"
        "    with open(r'C:\\Users\\23107\\ws_main_marker.log', 'a', encoding='utf-8') as _df:\n"
        "        _df.write(f'[MAIN_ENTER] pid={_diag_os.getpid()}\\n')\n"
        "except Exception:\n"
        "    pass\n\n"
    )
    
    new_text = text[:insert_at] + diag + text[insert_at:]
    open(src, 'w', encoding='utf-8').write(new_text)
    print(f'[1] DIAG inserted after from __future__, pos {insert_at}, size {len(new_text)}')

# 同步
mei_main = r'C:\Users\23107\AppData\Local\Temp\_MEIfull\app\main.py'
shutil.copy(src, mei_main)
print(f'[2] Copied to _MEIfull')

# 验证 - 显示前 350
v = open(mei_main, 'r', encoding='utf-8').read()
print(f'[3] First 350:')
print(v[:350])
