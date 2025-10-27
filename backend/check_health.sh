#!/bin/bash

#######################################
# PocketSpeak 后端健康检查脚本
# 版本: 1.0
#######################################

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 项目目录
BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$BACKEND_DIR/server.pid"
API_HOST="localhost"
API_PORT="8000"

echo -e "${BLUE}🏥 PocketSpeak 后端健康检查${NC}\n"
echo "=========================================="
echo

# 1. 检查进程状态
echo -e "${BLUE}[1] 检查进程状态${NC}"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 服务进程运行中 (PID: $PID)${NC}"
        # 显示进程信息
        ps -p $PID -o pid,ppid,%cpu,%mem,etime,cmd --no-headers
    else
        echo -e "${RED}❌ PID文件存在但进程不存在 (PID: $PID)${NC}"
        echo "  可能需要清理PID文件并重启服务"
    fi
else
    echo -e "${YELLOW}⚠️ 未找到PID文件${NC}"
    # 尝试查找进程
    PIDS=$(ps aux | grep "[p]ython main.py" | awk '{print $2}')
    if [ -n "$PIDS" ]; then
        echo -e "${YELLOW}  但找到相关进程: $PIDS${NC}"
    else
        echo -e "${RED}  服务未运行${NC}"
    fi
fi
echo

# 2. 检查端口监听
echo -e "${BLUE}[2] 检查端口监听${NC}"
if command -v netstat > /dev/null 2>&1; then
    if netstat -tuln | grep ":$API_PORT " > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 端口 $API_PORT 正在监听${NC}"
        netstat -tuln | grep ":$API_PORT "
    else
        echo -e "${RED}❌ 端口 $API_PORT 未监听${NC}"
    fi
elif command -v ss > /dev/null 2>&1; then
    if ss -tuln | grep ":$API_PORT " > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 端口 $API_PORT 正在监听${NC}"
        ss -tuln | grep ":$API_PORT "
    else
        echo -e "${RED}❌ 端口 $API_PORT 未监听${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ netstat/ss 命令不可用，跳过端口检查${NC}"
fi
echo

# 3. 测试HTTP健康检查接口
echo -e "${BLUE}[3] 测试HTTP健康检查${NC}"
if command -v curl > /dev/null 2>&1; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$API_HOST:$API_PORT/health 2>&1)
    if [ "$HTTP_STATUS" = "200" ]; then
        echo -e "${GREEN}✅ 健康检查接口响应正常 (HTTP $HTTP_STATUS)${NC}"
        RESPONSE=$(curl -s http://$API_HOST:$API_PORT/health)
        echo "  响应: $RESPONSE"
    else
        echo -e "${RED}❌ 健康检查接口异常 (HTTP $HTTP_STATUS)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ curl 命令不可用，跳过HTTP检查${NC}"
fi
echo

# 4. 测试单词查询API
echo -e "${BLUE}[4] 测试单词查询API${NC}"
if command -v curl > /dev/null 2>&1; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://$API_HOST:$API_PORT/api/words/lookup?word=test" 2>&1)
    if [ "$HTTP_STATUS" = "200" ]; then
        echo -e "${GREEN}✅ 单词查询API正常 (HTTP $HTTP_STATUS)${NC}"
    else
        echo -e "${YELLOW}⚠️ 单词查询API响应异常 (HTTP $HTTP_STATUS)${NC}"
        echo "  这可能是API密钥配置问题"
    fi
fi
echo

# 5. 检查系统资源
echo -e "${BLUE}[5] 系统资源使用${NC}"
echo -n "CPU: "
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1"%"}'
echo -n "内存: "
free -h | grep Mem | awk '{printf "已用: %s / 总计: %s (%.1f%%)\n", $3, $2, ($3/$2)*100}'
echo -n "磁盘: "
df -h $BACKEND_DIR | tail -1 | awk '{printf "已用: %s / 总计: %s (%s)\n", $3, $2, $5}'
echo

# 6. 检查日志文件
echo -e "${BLUE}[6] 检查日志文件${NC}"
LOG_FILE="$BACKEND_DIR/server.log"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    echo -e "${GREEN}✅ 日志文件存在: $LOG_FILE${NC}"
    echo "  文件大小: $LOG_SIZE"
    echo "  最后10行:"
    echo "  ----------------------------------------"
    tail -10 "$LOG_FILE" | sed 's/^/  /'
    echo "  ----------------------------------------"
else
    echo -e "${YELLOW}⚠️ 日志文件不存在${NC}"
fi
echo

# 总结
echo "=========================================="
echo -e "${BLUE}🎯 总结${NC}"

ALL_GOOD=true

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ! ps -p $PID > /dev/null 2>&1; then
        ALL_GOOD=false
    fi
else
    ALL_GOOD=false
fi

if command -v curl > /dev/null 2>&1; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$API_HOST:$API_PORT/health 2>&1)
    if [ "$HTTP_STATUS" != "200" ]; then
        ALL_GOOD=false
    fi
fi

if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}✅ 所有检查通过！服务运行正常${NC}"
    exit 0
else
    echo -e "${RED}❌ 存在问题，请查看上述检查结果${NC}"
    echo
    echo "💡 建议操作:"
    echo "  - 查看日志: tail -f $BACKEND_DIR/server.log"
    echo "  - 重启服务: ./stop_server.sh && ./start_server.sh"
    echo "  - 查看文档: cat DEPLOYMENT.md"
    exit 1
fi
