"""
精确解析 EXE 末尾 PyInstaller CArchive cookie (用 PyInstaller 6 真实格式)
"""
import struct, os

exe = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
print(f'EXE size: {os.path.getsize(exe):,} bytes')

with open(exe, 'rb') as f:
    data = f.read()

# PyInstaller 6 cookie format: !8sIIII64s  (网络字节序/大端)
_COOKIE_MAGIC_PATTERN = b'MEI\014\013\012\013\016'
_COOKIE_FORMAT = '!8sIIII64s'
_COOKIE_LENGTH = struct.calcsize(_COOKIE_FORMAT)
print(f'Cookie length: {_COOKIE_LENGTH} bytes')

# 找 MEI 位置
cookie_start = data.rfind(_COOKIE_MAGIC_PATTERN)
print(f'Cookie at offset: {cookie_start:,}')
print(f'Distance to end: {os.path.getsize(exe) - cookie_start} bytes')

# 读 cookie
cookie_data = data[cookie_start:cookie_start+_COOKIE_LENGTH]
print(f'Cookie hex: {cookie_data.hex()}')

magic, archive_length, toc_offset, toc_length, pyvers, pylib_name = struct.unpack(_COOKIE_FORMAT, cookie_data)
print(f'\n=== Cookie decoded ===')
print(f'  magic: {magic!r}')
print(f'  archive_length (pkg_length): {archive_length:,} bytes ({archive_length/1e6:.1f}MB)')
print(f'  toc_offset: {toc_offset:,}')
print(f'  toc_length: {toc_length:,} bytes ({toc_length/1e6:.1f}MB)')
print(f'  python_version: 0x{pyvers:08x}  ({pyvers})')
print(f'  python_libname: {pylib_name.rstrip(b"\\0").decode()!r}')

# 计算 start/end
end_offset = cookie_start + _COOKIE_LENGTH
start_offset = end_offset - archive_length
print(f'\n=== Archive positions ===')
print(f'  start_offset: {start_offset:,}')
print(f'  end_offset:   {end_offset:,}')
print(f'  archive size: {archive_length:,} ({archive_length/1e6:.1f}MB)')

# TOC 在 archive 内 offset 处
toc_data_start = start_offset + toc_offset
toc_data_end = toc_data_start + toc_length
print(f'  TOC data in EXE: {toc_data_start:,} - {toc_data_end:,}')

# 验证: archive 包含 PYZ 数据 + TOC
# 4820 entries, PYZ-00.pyz offset = 3267373170
# start_offset + 3267373170 = ?
print(f'\n=== PYZ entry position (from toc) ===')
print(f'  PYZ offset (from archive start): 3,267,373,170')
print(f'  + start_offset: {start_offset + 3267373170:,}')
print(f'  EXE size: {os.path.getsize(exe):,}')
