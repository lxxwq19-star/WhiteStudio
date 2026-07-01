"""
BiRefNet 模型预下载工具
- 国内网络友好：默认使用 hf-mirror.com
- 把模型权重 + 代码下载到 models_cache/<key>_local/
- 用户可一次下载、永久离线使用
"""
import os
import sys
import argparse

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

REPO_FILES = {
    "general": [
        "config.json",
        "birefnet.py",
        "BiRefNet_config.py",
        "model.safetensors",
    ],
    "matting": [
        "config.json",
        "birefnet.py",
        "BiRefNet_config.py",
        "model.safetensors",
    ],
    "portrait": [
        "config.json",
        "birefnet.py",
        "BiRefNet_config.py",
        "model.safetensors",
    ],
    "lite": [
        "config.json",
        "birefnet.py",
        "BiRefNet_config.py",
        "model.safetensors",
    ],
}

REPO_IDS = {
    "general": "ZhengPeng7/BiRefNet",
    "matting": "ZhengPeng7/BiRefNet-matting",
    "portrait": "ZhengPeng7/BiRefNet-portrait",
    "lite": "ZhengPeng7/BiRefNet_lite",
}


def _default_cache_root() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "models_cache")


def download(key: str, cache_root: str = None, mirror: str = None) -> str:
    """
    下载指定模型到本地，返回本地目录路径
    """
    if key not in REPO_IDS:
        raise ValueError(f"未知模型: {key}; 可选: {list(REPO_IDS)}")
    if cache_root is None:
        cache_root = _default_cache_root()
    local_dir = os.path.join(cache_root, f"{key}_local")
    os.makedirs(local_dir, exist_ok=True)
    repo_id = REPO_IDS[key]

    if mirror:
        os.environ["HF_ENDPOINT"] = mirror

    files = REPO_FILES[key]
    base_url = f"https://{os.environ['HF_ENDPOINT'].replace('https://', '').replace('http://', '')}/{repo_id}/resolve/main"

    print(f"[download] model={key}  repo={repo_id}")
    print(f"[download] to={local_dir}")
    print(f"[download] mirror={os.environ.get('HF_ENDPOINT')}")
    print()

    for fn in files:
        dst = os.path.join(local_dir, fn)
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            print(f"  ✓ {fn} (已存在 {os.path.getsize(dst)/1e6:.1f} MB)")
            continue
        url = f"{base_url}/{fn}"
        print(f"  ↓ {fn} ...")
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "WhiteStudio-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                total = r.length or -1
                downloaded = 0
                chunk = 1024 * 1024
                with open(dst, "wb") as f:
                    while True:
                        b = r.read(chunk)
                        if not b:
                            break
                        f.write(b)
                        downloaded += len(b)
                        if total > 0:
                            pct = downloaded * 100 / total
                            print(f"\r    {downloaded/1e6:.1f}/{total/1e6:.1f} MB ({pct:.1f}%)", end="", flush=True)
                print()
        except Exception as e:
            print(f"  ✗ {fn} 失败: {e}")
            raise

    print(f"\n[done] 模型 {key} 已就绪: {local_dir}")
    return local_dir


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", "-m", default="general", choices=list(REPO_IDS))
    p.add_argument("--cache", "-c", default=None)
    p.add_argument("--mirror", default=None,
                   help="镜像地址，默认 https://hf-mirror.com；可换 huggingface.co / 阿里镜像等")
    args = p.parse_args()
    download(args.model, args.cache, args.mirror)


if __name__ == "__main__":
    main()
