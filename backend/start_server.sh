#!/bin/bash

# PocketSpeak Backend 启动脚本
# 使用此脚本启动后端服务，确保路径正确配置

cd "$(dirname "$0")"

# 设置PYTHONPATH环境变量，将py-xiaozhi路径添加进去
export PYTHONPATH="${PYTHONPATH}:$(pwd)/libs/py_xiaozhi"

echo "🚀 启动 PocketSpeak Backend..."
echo "📁 PYTHONPATH: $PYTHONPATH"
echo ""

# 使用uvicorn直接启动，而不是通过python main.py
uvicorn main:app --reload --host 0.0.0.0 --port 8000
