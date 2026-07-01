"""
在 _MEIfull/app/main.py docstring 结束后插 DIAG
"""
import shutil

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\app\main.py'
dst = r'C:\Users\23107\AppData\Local\Temp\_MEIfull\app\main.py'
shutil.copy(src, dst)

# 也恢复 worker.py
shutil.copy(
    r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\app\worker.py',
    r'C:\Users\23107\AppData\Local\Temp\_MEIfull\app\worker.py',
)

content = open(dst, 'r', encoding='utf-8').read()
end_doc = content.find('"""', 3) + 3

diag = '\n\n# === DIAG (bypass test) ===\nimport os as _os\ntry:\n    with open(r"DIAG_PATH", "a") as _f:\n        _f.write(f"[MAIN_BYPASS_ENTER] pid={_os.getpid()}\n")\nexcept Exception:\n    pass\n'

# 用占位符方式写路径
marker = r'C:\Users\23107\ws_bypass_marker.log'
marker_escaped = marker.replace('\\', '\\\\')
diag = diag.replace('DIAG_PATH', marker_escaped)

new_content = content[:end_doc] + diag + content[end_doc:]
open(dst, 'w', encoding='utf-8').write(new_content)
print('Inserted DIAG after docstring at pos', end_doc)
print('First 400 chars:')
print(new_content[:400])
