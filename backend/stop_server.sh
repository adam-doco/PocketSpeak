#!/bin/bash

#######################################
# PocketSpeak 后端停止脚本
# 版本: 1.0
#######################################

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 项目目录
BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$BACKEND_DIR/server.pid"

echo -e "${YELLOW}🛑 停止 PocketSpeak 后端服务...${NC}\n"

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo -e "${RED}❌ 找不到PID文件，服务可能未运行${NC}"
    echo
    echo "尝试查找并停止相关进程..."
    # 尝试通过进程名查找
    PIDS=$(ps aux | grep "[p]ython main.py" | awk '{print $2}')
    if [ -z "$PIDS" ]; then
        echo "未找到运行中的服务进程"
        exit 1
    else
        echo "找到进程: $PIDS"
        kill $PIDS
        echo -e "${GREEN}✅ 已停止进程${NC}"
    fi
    exit 0
fi

# 读取PID
PID=$(cat "$PID_FILE")

# 检查进程是否存在
if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ 进程 $PID 不存在（可能已经停止）${NC}"
    rm -f "$PID_FILE"
    exit 0
fi

# 发送TERM信号
echo "发送停止信号 (PID: $PID)..."
kill $PID

# 等待进程结束
echo "等待进程结束..."
for i in {1..10}; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 服务已成功停止${NC}"
        rm -f "$PID_FILE"
        exit 0
    fi
    sleep 1
done

# 如果还没结束，强制kill
echo -e "${YELLOW}进程未响应，强制停止...${NC}"
kill -9 $PID 2>/dev/null

sleep 1

if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务已强制停止${NC}"
    rm -f "$PID_FILE"
else
    echo -e "${RED}❌ 无法停止服务，请检查进程状态${NC}"
    exit 1
fi
