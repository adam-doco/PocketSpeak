"""
PocketSpeak Backend 路径初始化模块
必须在导入其他模块之前执行，用于修复 py-xiaozhi 库的导入路径
"""

import sys
from pathlib import Path

# 获取当前文件所在目录（backend目录）
BACKEND_DIR = Path(__file__).parent

# 修复 py-xiaozhi 库的导入路径
# py-xiaozhi 内部使用 "from src.xxx" 导入，需要将其根目录加入 sys.path
py_xiaozhi_path = BACKEND_DIR / "libs" / "py_xiaozhi"

if py_xiaozhi_path.exists():
    py_xiaozhi_str = str(py_xiaozhi_path)
    if py_xiaozhi_str not in sys.path:
        sys.path.insert(0, py_xiaozhi_str)
        print(f"✅ py-xiaozhi 路径已添加: {py_xiaozhi_path}")
