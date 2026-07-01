"""
在源 main.py 早期加 DIAG, 然后同步到 _MEIfull
"""
import shutil, os

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\app\main.py'
text = open(src, 'r', encoding='utf-8').read()
end_doc = text.find('"""', 3) + 3

diag = (
    "\n\nimport os as _diag_os\n"
    "try:\n"
    "    with open(r'C:\\Users\\23107\\ws_main_marker.log', 'a', encoding='utf-8') as _df:\n"
    "        _df.write(f'[MAIN_ENTER] pid={_diag_os.getpid()}\\n')\n"
    "except Exception:\n"
    "    pass\n"
)

new_text = text[:end_doc] + diag + text[end_doc:]
open(src, 'w', encoding='utf-8').write(new_text)
print(f'[1] Source main.py updated, size {len(new_text)}')

# 同步到 _MEIfull
mei_main = r'C:\Users\23107\AppData\Local\Temp\_MEIfull\app\main.py'
shutil.copy(src, mei_main)
print(f'[2] Copied to {mei_main}')

# 验证
v = open(mei_main, 'r', encoding='utf-8').read()
print(f'[3] Verify: {v[end_doc:end_doc+250]}')
