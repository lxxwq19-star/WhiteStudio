#!/usr/bin/env python3
"""Download BiRefNet model weights for bundling into the macOS app."""
import os
import sys

os.environ["HF_ENDPOINT"] = "https://huggingface.co"

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("ERROR: huggingface_hub not installed. Run: pip install huggingface_hub")
    sys.exit(1)

print("=== Downloading BiRefNet model (general) ===")
snapshot_download(
    repo_id="ZhengPeng7/BiRefNet",
    local_dir="models_cache/general_local",
    local_dir_use_symlinks=False,
)
print("Model downloaded successfully to models_cache/general_local")
