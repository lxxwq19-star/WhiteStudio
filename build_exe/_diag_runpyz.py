"""
直接对 PKG 内部 offset 启动 ZlibArchiveReader, 看 PYZ 能否被 bootloader 读取
"""
import os
import struct
from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

src = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
reader = CArchiveReader(src)

# PYZ 在 PKG 内 offset
pyz_off_in_pkg = 3267373170  # from earlier
pyz_start_in_exe = reader._start_offset + pyz_off_in_pkg
print(f'PKG start in EXE: {reader._start_offset:,}')
print(f'PYZ offset in PKG: {pyz_off_in_pkg:,}')
print(f'PYZ offset in EXE: {pyz_start_in_exe:,}')

# 不解压直接打开
# ZlibArchiveReader(filename, start_offset)
pyzr = ZlibArchiveReader(src, start_offset=pyz_start_in_exe)
print(f'\\nZlibArchiveReader opened from EXE memory!')
print(f'  PYZ modules: {len(pyzr.toc)}')
print(f'  First 5: {list(pyzr.toc.keys())[:5]}')

# 验证 PYZ magic
with open(src, 'rb') as f:
    f.seek(pyz_start_in_exe)
    magic = f.read(4)
print(f'\\n  Magic at offset: {magic!r}  (expect b"PYZ\\x00")')

# 读 PYZ header: PYZ\\0 + pymagic(4) + toc_offset(4)
# See pyimod01_archive.py:
#   magic = fp.read(len(self._PYZ_MAGIC_PATTERN))  # 4 bytes
#   pymagic = fp.read(len(PYTHON_MAGIC_NUMBER))    # 4 bytes
#   toc_offset, *_ = struct.unpack('!i', fp.read(4))
with open(src, 'rb') as f:
    f.seek(pyz_start_in_exe)
    header = f.read(64)
print(f'\\n  PYZ first 64 bytes: {header[:12].hex()}')
import struct
toc_offset = struct.unpack('!i', header[8:12])[0]
print(f'  TOC offset (in PYZ, big-endian int32): {toc_offset:,}')
print(f'  TOC offset in EXE: {pyz_start_in_exe + toc_offset:,}')
