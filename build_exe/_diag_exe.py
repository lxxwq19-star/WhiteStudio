import os
exe = r'C:\Users\23107\.qclaw\workspace\birefnet_whitestudio\dist\WhiteStudio.exe'
size = os.path.getsize(exe)
print(f'EXE size: {size:,} bytes ({size/1e6:.1f}MB)')

with open(exe, 'rb') as f:
    data = f.read()

# 1. PyInstaller PYZ magic
print(f'PYZ magic PYZ\\0 count: {data.count(b"PYZ\x00")}')

# 2. PYZ-00.pyz filename
print(f'PYZ-00.pyz name count: {data.count(b"PYZ-00.pyz")}')

# 3. WhiteStudio CArchive name
ws = b'WhiteStudio'
print(f'WhiteStudio name count: {data.count(ws)}')

# 4. MEI archive magic
mei = b'MEI\x0c\x0b\x0a\x0b\x0e'
print(f'CArchive MEI magic count: {data.count(mei)}')

# 5. 找 MEI magic 的 offset
import re
for m in re.finditer(re.escape(mei), data):
    print(f'  MEI offset: {m.start():,}')
    if m.start() < len(data) - 64:
        # 看后面 24 字节 - CArchive header
        # struct {char magic[8]; uint32 len; uint32 toc_offset; uint32 toc_len; ...}
        import struct
        hdr = data[m.start():m.start()+64]
        print(f'    next 64 bytes: {hdr.hex()}')
        if len(hdr) >= 24:
            pkg_len, toc_offset, toc_len = struct.unpack('<III', hdr[8:20])
            print(f'    pkg_len={pkg_len:,} ({pkg_len/1e6:.1f}MB)  toc_offset={toc_offset:,}  toc_len={toc_len:,}')

# 6. Tail 32 bytes
print(f'\nTail 32 bytes hex: {data[-32:].hex()}')
