"""
反编译 _MEIfull/run 看 run.py 在 EXE 里的逻辑
"""
import marshal, dis, struct
mei = r'C:\Users\23107\AppData\Local\Temp\_MEIfull'
data = open(mei + '/run', 'rb').read()
print(f'Size: {len(data)} bytes')
print(f'Hex: {data[:32].hex()}')
# type='s' 在 PyInstaller 6 中是 .py 源 (字节码) — 需要 .pyc magic + magic + timestamp + size + source
# 在 PyInstaller 6.0+ type='s' 是 PYSOURCE (字节码), 没有 header, 直接 marshal
# 试 marshal 直接 load
try:
    code = marshal.loads(data)
    print('Marshal OK')
    print('Filename:', code.co_filename)
    print('Names:', code.co_names)
    print('Constants:')
    for c in code.co_consts[:5]:
        if hasattr(c, 'co_filename'):
            print(f'  Code: {c.co_filename}')
        else:
            print(f'  {c!r}')
except Exception as e:
    print(f'Marshal fail: {e}')
    # 可能需要 16 字节 header (4 magic + 4 flags + 4 timestamp + 4 size)
    if data[:4] in (b'\\xe3\\x00\\x00\\x00', b'\\xcb\\x0d\\x0d\\x0a'):
        print('Looks like .pyc header, trying skip 16 bytes')
        try:
            code = marshal.loads(data[16:])
            print('Skip 16 marshal OK')
        except Exception as e2:
            print(f'Skip 16 fail: {e2}')
