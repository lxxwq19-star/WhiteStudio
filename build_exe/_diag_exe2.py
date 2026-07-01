import os, struct

exe = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
size = os.path.getsize(exe)
print(f'EXE size: {size:,} bytes')

with open(exe, 'rb') as f:
    data = f.read()

# PyInstaller CArchive header (从 PyInstaller archive_viewer.py)
# struct: 
#   cookie = struct.Struct('!8sIIIII')  # 大端! 但实际是 PKG 头
# 实际是:
#   _cookie_format = "8sIIIIIII64s"  magic(8) + len(4) + TOC(4) + TOCLen(4) + pyver(4) + pylibname_len(4) + 2 unused + pylibname(64)
# 大端 8s + IIIII + 64s
# Magic = b'MEI\014\013\012\013\016'
mei = b'MEI\x0c\x0b\x0a\x0b\x0e'
idx = data.rfind(mei)
print(f'MEI magic at offset: {idx:,} (size={size:,}, dist to end: {size-idx} bytes)')

# Read 64 bytes
hdr = data[idx:idx+64]
print(f'\n64-byte header hex: {hdr.hex()}')

# Try different struct formats
for fmt_name, fmt in [
    ('big-endian 8s IIIII 64s', '>8sIIIII64s'),
    ('little-endian 8s IIIII 64s', '<8sIIIII64s'),
    ('big-endian 8s I 5I 64s', '>8sI5I64s'),
]:
    try:
        m, a, b, c, d, e, f = struct.unpack(fmt, hdr)
        print(f'\n[{fmt_name}]')
        print(f'  magic={m!r}  a={a:,}  b={b:,}  c={c:,}  d={d:,}  e={e:,}  f={f[:30]!r}...')
    except Exception as ex:
        print(f'  [{fmt_name}] error: {ex}')

# 找 PYZ 字节 (PYZ\0 在 PYZ 归档 CArchive 内部)
# PyInstaller PYZ CArchive uses magic = b'PYZ\x00'
pyz_magic = b'PYZ\x00'
pyz_idx = data.find(pyz_magic)
print(f'\nPYZ magic at offset: {pyz_idx:,}')

if pyz_idx > 0:
    # PYZ CArchive header
    # struct: 8s IIIII
    phdr = data[pyz_idx:pyz_idx+24]
    print(f'PYZ hdr hex: {phdr.hex()}')
    # PYZ 包结构: magic(8) + pkg_len(4) + toc_off(4) + toc_len(4) + python_version(4)
    pkg_len, toc_off, toc_len, pyver = struct.unpack('<IIII', data[pyz_idx+8:pyz_idx+24])
    print(f'  pkg_len={pkg_len:,} ({pkg_len/1e6:.1f}MB)  toc_off={toc_off:,}  toc_len={toc_len:,}  pyver=0x{pyver:08x}')

# 关键: 实际 PKG CArchive 起始位置在哪里?
# 应该是 bootloader 末尾 + TOC 末尾往前
# 试试 rfind 找 PYZ 之前的内容
