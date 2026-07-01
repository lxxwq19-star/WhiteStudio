"""
一键下载 BiRefNet 4 个非通用权重到本地缓存
下载完直接能用 EXE 切换 dropdown 选 portrait/matting/lite/dynamic

用法: python download_all_weights.py [portrait] [matting] [lite] [dynamic]
      不带参数 = 下载全部 4 个
"""
import os
import sys
from pathlib import Path

# 国内镜像（必须！）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from huggingface_hub import snapshot_download

REPO_ROOT = Path(__file__).resolve().parent
CACHE_DIR = REPO_ROOT / "models_cache"
CACHE_DIR.mkdir(exist_ok=True)

# (本地子目录名, HuggingFace 仓库 ID)
WEIGHTS = [
    ("portrait", "ZhengPeng7/BiRefNet-portrait"),
    ("matting",  "ZhengPeng7/BiRefNet-matting"),
    ("lite",     "ZhengPeng7/BiRefNet_lite"),
    ("dynamic",  "ZhengPeng7/BiRefNet_dynamic"),
]

# 只下核心文件，避免 handler.py 之类不需要的
ALLOW_PATTERNS = [
    "*.json",
    "*.py",
    "*.safetensors",
    "*.txt",
    "*.md",          # 顺便下 README
]

def download_one(local_name: str, repo_id: str):
    local_dir = CACHE_DIR / f"{local_name}_local"
    if (local_dir / "config.json").exists() and (local_dir / "model.safetensors").exists():
        print(f"[跳过] {local_name}: 已有本地缓存 {local_dir}")
        return
    print(f"\n[开始] {local_name} ← {repo_id}")
    print(f"  目标: {local_dir}")
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        allow_patterns=ALLOW_PATTERNS,
        etag_timeout=30,
    )
    # 列出下载结果
    files = sorted(local_dir.iterdir()) if local_dir.exists() else []
    print(f"[完成] {local_name}: {len(files)} 个文件")
    for f in files:
        size = f.stat().st_size
        if size > 1024 * 1024:
            print(f"  {f.name:30s} {size/1024/1024:.1f} MB")
        else:
            print(f"  {f.name:30s} {size} B")

def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else [w[0] for w in WEIGHTS]
    print(f"将下载权重: {targets}")
    print(f"缓存目录:   {CACHE_DIR}\n")
    for local_name, repo_id in WEIGHTS:
        if local_name in targets:
            try:
                download_one(local_name, repo_id)
            except Exception as e:
                print(f"[失败] {local_name}: {e}")
    print("\n[全部完成] 现在可以重启 EXE 切换权重了")

if __name__ == "__main__":
    main()
