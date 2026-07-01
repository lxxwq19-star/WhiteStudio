from PyInstaller.archive.readers import CArchiveReader
reader = CArchiveReader('dist/WhiteStudio.exe')
toc = reader.toc
print(f'len(toc)={len(toc)}, type={type(toc)}')

# 取一个看结构
for name in list(toc.keys())[:3]:
    val = toc[name]
    print(f'  {name!r} -> {val} type={type(val)}')
print()
# 找 PYZ
for name in toc:
    if 'PYZ' in str(name):
        print(f'  PYZ entry: {toc[name]}')
        break
# 找 main
for name in toc:
    if str(name) in ('WhiteStudio', 'WhiteStudio.exe', 'run', 'run.py'):
        print(f'  Main entry: {toc[name]}')
        break
