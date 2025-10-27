#!/bin/bash

#######################################
# PocketSpeak 后端一键部署脚本
# 适用于 Ubuntu 22.04/20.04
# 版本: 1.0
#######################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_DIR="$HOME/PocketSpeak"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="$BACKEND_DIR/venv"
PYTHON_VERSION="3.11"
REPO_URL="https://github.com/adam-doco/PocketSpeak.git"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_section() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN} $1${NC}"
    echo -e "${GREEN}========================================${NC}\n"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查Python版本
check_python_version() {
    if command_exists python$PYTHON_VERSION; then
        print_success "Python $PYTHON_VERSION 已安装"
        return 0
    else
        print_warning "Python $PYTHON_VERSION 未安装"
        return 1
    fi
}

# 安装Python
install_python() {
    print_section "安装 Python $PYTHON_VERSION"

    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install -y python$PYTHON_VERSION python$PYTHON_VERSION-venv python$PYTHON_VERSION-dev

    print_success "Python $PYTHON_VERSION 安装完成"
}

# 安装系统依赖
install_system_dependencies() {
    print_section "安装系统依赖"

    sudo apt update
    sudo apt install -y \
        git \
        curl \
        wget \
        vim \
        build-essential \
        python3-pip

    print_success "系统依赖安装完成"
}

# 克隆项目
clone_project() {
    print_section "克隆项目"

    if [ -d "$PROJECT_DIR" ]; then
        print_warning "项目目录已存在: $PROJECT_DIR"
        read -p "是否删除并重新克隆? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "删除现有目录..."
            rm -rf "$PROJECT_DIR"
        else
            print_info "使用现有目录，执行 git pull..."
            cd "$PROJECT_DIR"
            git pull origin main
            print_success "代码更新完成"
            return 0
        fi
    fi

    print_info "从 GitHub 克隆项目..."
    git clone "$REPO_URL" "$PROJECT_DIR"

    cd "$PROJECT_DIR"

    # 初始化子模块
    if [ -f ".gitmodules" ]; then
        print_info "初始化 Git 子模块..."
        git submodule init
        git submodule update
    fi

    print_success "项目克隆完成"
}

# 创建Python虚拟环境
create_venv() {
    print_section "创建 Python 虚拟环境"

    if [ -d "$VENV_DIR" ]; then
        print_warning "虚拟环境已存在，跳过创建"
        return 0
    fi

    print_info "创建虚拟环境..."
    cd "$BACKEND_DIR"
    python$PYTHON_VERSION -m venv venv

    print_success "虚拟环境创建完成"
}

# 安装Python依赖
install_python_dependencies() {
    print_section "安装 Python 依赖"

    cd "$BACKEND_DIR"
    source venv/bin/activate

    print_info "升级 pip..."
    pip install --upgrade pip

    print_info "安装依赖包..."
    pip install -r requirements.txt

    # 安装额外依赖
    print_info "安装额外依赖..."
    pip install httpx pyyaml

    print_success "Python 依赖安装完成"
}

# 配置数据目录
setup_data_directory() {
    print_section "配置数据目录"

    cd "$BACKEND_DIR"

    # 创建data目录
    mkdir -p data

    # 创建初始数据文件（如果不存在）
    if [ ! -f data/users.json ]; then
        echo '[]' > data/users.json
        print_info "创建 users.json"
    fi

    if [ ! -f data/vocab_favorites.json ]; then
        echo '[]' > data/vocab_favorites.json
        print_info "创建 vocab_favorites.json"
    fi

    # 设置权限
    chmod 755 data
    chmod 644 data/*.json 2>/dev/null || true

    print_success "数据目录配置完成"
}

# 配置API密钥
configure_api_keys() {
    print_section "配置 API 密钥"

    CONFIG_FILE="$BACKEND_DIR/config/external_apis.yaml"

    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        return 1
    fi

    print_warning "请手动编辑配置文件添加API密钥:"
    print_info "配置文件路径: $CONFIG_FILE"
    echo
    print_info "需要配置以下API密钥:"
    echo "  1. DeepSeek AI API Key"
    echo "  2. 豆包 AI API Key 和 Endpoint ID"
    echo "  3. 有道翻译 APP ID 和 APP Key"
    echo
    read -p "按回车键继续编辑配置文件..." -r

    vim "$CONFIG_FILE"

    print_success "配置文件编辑完成"
}

# 测试服务
test_service() {
    print_section "测试服务"

    cd "$BACKEND_DIR"
    source venv/bin/activate

    print_info "启动服务进行测试（20秒后自动停止）..."
    print_info "如果看到 'Uvicorn running' 说明启动成功"
    echo

    # 后台启动服务
    timeout 20 python main.py &
    SERVER_PID=$!

    # 等待服务启动
    sleep 5

    # 测试健康检查
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "✅ 服务测试成功！"
    else
        print_warning "⚠️ 服务可能未成功启动，请检查日志"
    fi

    # 停止测试服务
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
}

# 配置systemd服务
setup_systemd_service() {
    print_section "配置 systemd 服务"

    read -p "是否配置 systemd 服务（开机自启）? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "跳过 systemd 配置"
        return 0
    fi

    SERVICE_FILE="/etc/systemd/system/pocketspeak.service"

    print_info "创建 systemd 服务文件..."
    sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=PocketSpeak Backend API Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BACKEND_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python main.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    print_info "重新加载 systemd 配置..."
    sudo systemctl daemon-reload

    print_info "启用服务..."
    sudo systemctl enable pocketspeak

    print_info "启动服务..."
    sudo systemctl start pocketspeak

    # 等待服务启动
    sleep 3

    # 检查服务状态
    if sudo systemctl is-active --quiet pocketspeak; then
        print_success "✅ systemd 服务配置成功并已启动"
        echo
        sudo systemctl status pocketspeak --no-pager -l
    else
        print_error "❌ 服务启动失败，请检查日志:"
        echo "  sudo journalctl -u pocketspeak -n 50"
    fi
}

# 显示部署信息
show_deployment_info() {
    print_section "部署完成"

    echo -e "${GREEN}🎉 PocketSpeak 后端部署成功！${NC}\n"

    # 获取公网IP
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || echo "unknown")

    echo "📍 部署信息:"
    echo "  - 项目目录: $PROJECT_DIR"
    echo "  - 后端目录: $BACKEND_DIR"
    echo "  - 虚拟环境: $VENV_DIR"
    echo "  - 配置文件: $BACKEND_DIR/config/external_apis.yaml"
    echo
    echo "🌐 访问地址:"
    echo "  - 本地: http://localhost:8000"
    echo "  - 公网: http://$PUBLIC_IP:8000"
    echo "  - 健康检查: http://$PUBLIC_IP:8000/health"
    echo
    echo "🔧 服务管理命令:"
    echo "  - 启动: sudo systemctl start pocketspeak"
    echo "  - 停止: sudo systemctl stop pocketspeak"
    echo "  - 重启: sudo systemctl restart pocketspeak"
    echo "  - 状态: sudo systemctl status pocketspeak"
    echo "  - 日志: sudo journalctl -u pocketspeak -f"
    echo
    echo "📖 完整文档: $BACKEND_DIR/DEPLOYMENT.md"
    echo
    print_warning "⚠️ 重要提示:"
    echo "  1. 请确保AWS安全组已开放 8000 端口"
    echo "  2. 请检查API密钥配置是否正确"
    echo "  3. 建议配置Nginx反向代理和HTTPS"
    echo
}

# 主流程
main() {
    clear
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════╗"
    echo "║   PocketSpeak 后端一键部署脚本       ║"
    echo "║   版本: 1.0                            ║"
    echo "╚════════════════════════════════════════╝"
    echo -e "${NC}\n"

    print_info "开始部署流程..."
    echo

    # 1. 检查并安装Python
    if ! check_python_version; then
        install_python
    fi

    # 2. 安装系统依赖
    install_system_dependencies

    # 3. 克隆项目
    clone_project

    # 4. 创建虚拟环境
    create_venv

    # 5. 安装Python依赖
    install_python_dependencies

    # 6. 配置数据目录
    setup_data_directory

    # 7. 配置API密钥
    configure_api_keys

    # 8. 测试服务
    test_service

    # 9. 配置systemd服务
    setup_systemd_service

    # 10. 显示部署信息
    show_deployment_info
}

# 运行主流程
main "$@"
