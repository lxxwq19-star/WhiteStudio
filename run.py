"""
WhiteStudio 启动入口
用法：
  python run.py            # 启动 GUI
"""
import sys
import os

# 防止打包后找不到模块
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from app.main import main

if __name__ == "__main__":
    main()
