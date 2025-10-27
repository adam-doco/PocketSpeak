#!/bin/bash

#######################################
# PocketSpeak 后端启动脚本
# 版本: 1.0
#######################################

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# 项目目录
BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$BACKEND_DIR/venv"
PID_FILE="$BACKEND_DIR/server.pid"
LOG_FILE="$BACKEND_DIR/server.log"

echo -e "${GREEN}🚀 启动 PocketSpeak 后端服务...${NC}\n"

# 检查虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ 虚拟环境不存在: $VENV_DIR${NC}"
    echo "请先运行部署脚本: ./deploy.sh"
    exit 1
fi

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${RED}❌ 服务已经在运行中 (PID: $OLD_PID)${NC}"
        echo "如需重启，请先运行: ./stop_server.sh"
        exit 1
    else
        # PID文件存在但进程不存在，删除旧PID文件
        rm -f "$PID_FILE"
    fi
fi

# 进入后端目录
cd "$BACKEND_DIR"

# 激活虚拟环境并启动服务
echo "📂 工作目录: $BACKEND_DIR"
echo "🐍 虚拟环境: $VENV_DIR"
echo "📝 日志文件: $LOG_FILE"
echo

source "$VENV_DIR/bin/activate"

# 后台启动服务
nohup python main.py > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

# 保存PID
echo $SERVER_PID > "$PID_FILE"

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 3

# 检查服务是否成功启动
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务启动成功！${NC}"
    echo
    echo "📊 服务信息:"
    echo "  - PID: $SERVER_PID"
    echo "  - 端口: 8000"
    echo "  - 日志: $LOG_FILE"
    echo
    echo "🌐 访问地址:"
    echo "  - 本地: http://localhost:8000"
    echo "  - 健康检查: http://localhost:8000/health"
    echo
    echo "💡 有用的命令:"
    echo "  - 查看日志: tail -f $LOG_FILE"
    echo "  - 停止服务: ./stop_server.sh"
    echo "  - 检查状态: ./check_health.sh"
    echo

    # 测试健康检查
    sleep 2
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 健康检查通过${NC}"
    else
        echo -e "${RED}⚠️ 健康检查失败，请查看日志${NC}"
    fi
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    echo "请查看日志: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
