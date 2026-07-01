"""
WhiteStudio 打包脚本
一键清理 + 构建 + 验证
"""
import os
import sys
import shutil
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = PROJECT_ROOT / "build_exe"
DIST_DIR = PROJECT_ROOT / "dist"
SPEC_FILE = BUILD_DIR / "WhiteStudio.spec"
EXE_NAME = "WhiteStudio.exe"

# 颜色 (Windows 10+ ANSI)
os.system("")


def cprint(text: str, color: str = ""):
    colors = {
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "reset": "\033[0m",
    }
    c = colors.get(color, "")
    print(f"{c}{text}{colors['reset']}")


def fmt_size(size_bytes: int) -> str:
    """格式化字节数"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def clean():
    """清理旧的构建产物"""
    cprint("\n[1/4] 清理旧构建产物...", "cyan")
    for p in [DIST_DIR, PROJECT_ROOT / "build"]:
        if p.exists():
            cprint(f"  - 删除 {p}", "yellow")
            shutil.rmtree(p, ignore_errors=True)
    cprint("  ✓ 清理完成", "green")


def build():
    """调用 PyInstaller 构建"""
    cprint("\n[2/4] 启动 PyInstaller 打包...", "cyan")
    cprint(f"  spec: {SPEC_FILE}", "white")
    cprint(f"  预计耗时 8-15 分钟 (PyInstaller 分析 torch 很慢)", "yellow")

    t0 = time.time()
    # 用子进程跑, 实时显示输出
    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm", "--clean"]
    cprint(f"  cmd: {' '.join(cmd)}", "white")
    print()

    # 不捕获, 实时输出
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    elapsed = time.time() - t0
    if result.returncode != 0:
        cprint(f"\n  ✗ PyInstaller 失败 (耗时 {elapsed:.0f}s)", "red")
        sys.exit(1)

    cprint(f"\n  ✓ 打包成功 (耗时 {elapsed:.0f}s)", "green")


def verify():
    """验证产物"""
    cprint("\n[3/4] 验证产物...", "cyan")
    exe_path = DIST_DIR / EXE_NAME
    if not exe_path.exists():
        cprint(f"  ✗ 找不到 {exe_path}", "red")
        sys.exit(1)

    size = exe_path.stat().st_size
    cprint(f"  ✓ exe 路径: {exe_path}", "green")
    cprint(f"  ✓ exe 大小: {fmt_size(size)}", "green")

    if size < 2 * 1024**3:
        cprint(f"  ⚠ exe 体积小于 2GB, 可能有依赖未打入", "yellow")
    elif size > 3.5 * 1024**3:
        cprint(f"  ⚠ exe 体积超过 3.5GB, 可能打入了多余资源", "yellow")


def generate_readme():
    """生成 README"""
    cprint("\n[4/4] 生成 README...", "cyan")
    readme = f"""WhiteStudio · BiRefNet 一键批量扣图加白底 v1.0 (测试版)
=============================================================

📦 文件清单
-----------
- WhiteStudio.exe    主程序 ({fmt_size((DIST_DIR / EXE_NAME).stat().st_size) if (DIST_DIR / EXE_NAME).exists() else "2.5GB 左右"})

🚀 使用方法
-----------
1. 确认目标机器满足以下条件:
   - Windows 10 (1809+) 或 Windows 11 (64位)
   - NVIDIA 独显 (RTX 20/30/40 系列或更新)
   - 已安装 NVIDIA 显卡驱动 ≥ 528.33 (推荐最新 Game Ready)
   - 已安装 Microsoft Visual C++ 2015-2022 Redistributable (x64)
   - C 盘剩余空间 ≥ 5 GB
2. 双击 WhiteStudio.exe 运行
3. 首次启动需要 30-60 秒解压 (Windows Defender 可能询问, 选"仍要运行")
4. 添加图片 → 调整参数 → 点"开始处理"

⚙️ 依赖下载
-----------
- NVIDIA 显卡驱动: https://www.nvidia.com/Download/index.aspx
  (如已安装, 可用 nvidia-smi 命令验证)
- VC++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe
  (Win11 默认有, Win10 多数也有)

❓ 常见问题
-----------
Q: 双击 exe 没反应?
A: 等待 30-60 秒 (首次解压); 检查 Windows Defender 是否隔离了文件;
   尝试右键 → 以管理员身份运行。

Q: 启动报 "ImportError: No module named xxx"?
A: 反馈给开发者, 需要补 hiddenimports。

Q: 启动报 "CUDA not available"?
A: 确认装了 NVIDIA 驱动 (nvidia-smi 能看到显卡);
   老显卡 (<Pascal 架构) 不支持。

Q: 启动报 "Microsoft Visual C++ 14.0 or greater is required"?
A: 下载安装 vc_redist.x64.exe (链接见上)。

Q: 推理报 "out of memory"?
A: 调小"输入尺寸"滑块 (1024 → 768), 或减小"批大小" (默认 1)。

📞 反馈
-------
打包/运行有任何问题, 把以下信息一起发回:
1. nvidia-smi 输出截图
2. 启动时的弹窗截图 / 控制台日志
3. 项目源码版本 (git log -1 或 文件 hash)

🎉 祝测试顺利!
"""
    readme_path = DIST_DIR / "README.txt"
    readme_path.write_text(readme, encoding="utf-8")
    cprint(f"  ✓ README 已生成: {readme_path}", "green")


def main():
    cprint("=" * 60, "cyan")
    cprint("  WhiteStudio 打包工具", "cyan")
    cprint("=" * 60, "cyan")
    cprint(f"  项目根: {PROJECT_ROOT}", "white")
    cprint(f"  入口:   {PROJECT_ROOT / 'run.py'}", "white")
    cprint(f"  权重:   {PROJECT_ROOT / 'models_cache' / 'birefnet_local'}", "white")

    clean()
    build()
    verify()
    generate_readme()

    cprint("\n" + "=" * 60, "green")
    cprint("  ✅ 全部完成!", "green")
    cprint("=" * 60, "green")
    cprint(f"\n  产物: {DIST_DIR}", "white")
    cprint(f"  请用 U盘/网盘 分发给测试同事", "yellow")


if __name__ == "__main__":
    main()
