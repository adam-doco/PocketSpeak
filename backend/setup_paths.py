"""
PocketSpeak Backend 路径初始化模块
必须在导入其他模块之前执行，用于修复 py-xiaozhi 库的导入路径
"""

import sys
from pathlib import Path

# 获取当前文件所在目录（backend目录）
BACKEND_DIR = Path(__file__).parent

# 确保 backend 目录在 sys.path 中（用于导入 utils, deps 等模块）
backend_str = str(BACKEND_DIR)
if backend_str not in sys.path and str(BACKEND_DIR.resolve()) not in sys.path:
    sys.path.insert(0, backend_str)
    print(f"✅ Backend 路径已添加: {BACKEND_DIR}")
else:
    print(f"ℹ️  Backend 路径已存在于 sys.path")

# 修复 py-xiaozhi 库的导入路径
# py-xiaozhi 内部使用 "from src.xxx" 导入，需要将其根目录加入 sys.path
py_xiaozhi_path = BACKEND_DIR / "libs" / "py_xiaozhi"

if py_xiaozhi_path.exists():
    py_xiaozhi_str = str(py_xiaozhi_path)
    if py_xiaozhi_str not in sys.path:
        sys.path.insert(0, py_xiaozhi_str)
        print(f"✅ py-xiaozhi 路径已添加: {py_xiaozhi_path}")
